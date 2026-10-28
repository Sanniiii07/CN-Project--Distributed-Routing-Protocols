"""
Distance Vector Routing Protocol Implementation.
Uses the Bellman-Ford algorithm to compute shortest paths based on
distance vectors received from direct neighbours.
Includes unreachable route handling (INFINITY = 16) and Split Horizon loop prevention.
"""

import os
import sys
from typing import Dict, List, Optional, Set

# Ensure project root is accessible for imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from router.routing_table import RoutingTable, INFINITY

# Loop prevention mode constants
LOOP_PREVENTION_NONE = "NONE"
LOOP_PREVENTION_SPLIT_HORIZON = "SPLIT_HORIZON"
LOOP_PREVENTION_POISONED_REVERSE = "POISONED_REVERSE"


class DistanceVectorNode:
    """
    A Distance Vector routing engine for a single router.
    Calculates candidate route costs using the Bellman-Ford equation:
      D_x(y) = min_v { c(x, v) + D_v(y) }
    Supports Split Horizon to prevent routing loops between adjacent nodes.
    """

    def __init__(
        self,
        router_id: str,
        neighbours: Optional[Dict[str, float]] = None,
        loop_prevention: str = LOOP_PREVENTION_NONE
    ):
        self.router_id = str(router_id)
        self.loop_prevention = loop_prevention.upper()

        # Direct link costs to active neighbours: {neighbour_id: link_cost}
        self.neighbours: Dict[str, float] = {}
        if neighbours:
            for nbr, cost in neighbours.items():
                self.neighbours[str(nbr)] = float(cost)

        # Main routing table: stores best known cost, next hop, and reachability
        self.routing_table = RoutingTable(owner_id=self.router_id)

        # Vectors received from direct neighbours: {neighbour_id: {destination: cost}}
        self.neighbour_vectors: Dict[str, Dict[str, float]] = {}

        # Initialize direct neighbours into routing table
        for nbr, cost in self.neighbours.items():
            self.routing_table.update_route(destination=nbr, cost=cost, next_hop=nbr)

    def set_neighbour_cost(self, neighbour_id: str, cost: float) -> bool:
        """
        Updates the local link cost to a direct neighbour.
        Triggers route recalculation.
        """
        neighbour_id = str(neighbour_id)
        cost = float(cost)
        self.neighbours[neighbour_id] = cost
        return self.recalculate_routes()

    def fail_link(self, neighbour_id: str) -> bool:
        """
        Simulates a direct link failure to a neighbour.
        Removes the neighbour from active links and clears its stored vector.
        Recalculates routes so destinations routed through it become unreachable or rerouted.
        """
        neighbour_id = str(neighbour_id)
        if neighbour_id in self.neighbours:
            del self.neighbours[neighbour_id]
            self.neighbour_vectors.pop(neighbour_id, None)
            return self.recalculate_routes()
        return False

    def recover_link(self, neighbour_id: str, cost: float) -> bool:
        """
        Restores a direct link to a neighbour with the given cost.
        """
        neighbour_id = str(neighbour_id)
        self.neighbours[neighbour_id] = float(cost)
        return self.recalculate_routes()

    def receive_vector(self, neighbour_id: str, vector: Dict[str, float]) -> bool:
        """
        Receives a distance vector advertised by a direct neighbour.
        Stores the vector and recalculates routes.
        Returns True if any route in the local routing table changed.
        """
        neighbour_id = str(neighbour_id)
        if neighbour_id not in self.neighbours:
            # Drop vectors from neighbours whose links are currently down/inactive
            return False

        # Store received vector (capping costs at INFINITY)
        self.neighbour_vectors[neighbour_id] = {
            str(dest): min(float(cost), INFINITY) for dest, cost in vector.items()
        }

        # Recalculate routes using the new information
        return self.recalculate_routes()

    def recalculate_routes(self) -> bool:
        """
        Runs the Bellman-Ford calculation across all known destinations:
          D_x(y) = min_v { c(x, v) + D_v(y) }
        If no path with cost < INFINITY exists, the destination is marked UNREACHABLE.
        Returns True if the routing table changed.
        """
        changed = False

        # Gather all known destinations
        all_destinations: Set[str] = {self.router_id}
        all_destinations.update(self.neighbours.keys())
        all_destinations.update(self.routing_table.get_all_destinations())
        for vector in self.neighbour_vectors.values():
            all_destinations.update(vector.keys())

        for dest in all_destinations:
            # Route to self is always cost 0 via self
            if dest == self.router_id:
                if self.routing_table.get_cost(dest) != 0.0:
                    self.routing_table.update_route(dest, cost=0.0, next_hop=self.router_id)
                    changed = True
                continue

            best_cost = INFINITY
            best_next_hop: Optional[str] = None

            # Option 1: Direct link (if destination is an active direct neighbour)
            if dest in self.neighbours:
                direct_cost = self.neighbours[dest]
                if direct_cost < best_cost:
                    best_cost = direct_cost
                    best_next_hop = dest

            # Option 2: Paths via each active direct neighbour v using Bellman-Ford
            for nbr, link_cost in self.neighbours.items():
                nbr_vector = self.neighbour_vectors.get(nbr, {})
                if dest in nbr_vector:
                    nbr_cost = nbr_vector[dest]
                    if nbr_cost < INFINITY:
                        total_cost = link_cost + nbr_cost
                        if total_cost < best_cost:
                            best_cost = min(total_cost, INFINITY)
                            best_next_hop = nbr

            # Check if route state changed
            old_cost = self.routing_table.get_cost(dest)
            old_hop = self.routing_table.get_next_hop(dest)

            if best_cost >= INFINITY:
                # Destination is unreachable
                if old_cost < INFINITY or old_hop is not None:
                    self.routing_table.mark_unreachable(dest)
                    changed = True
            else:
                # Destination is reachable with a valid route
                if old_cost != best_cost or old_hop != best_next_hop:
                    self.routing_table.update_route(dest, cost=best_cost, next_hop=best_next_hop)
                    changed = True

        return changed

    def get_outgoing_vector(self, for_neighbour: Optional[str] = None) -> Dict[str, float]:
        """
        Returns the Distance Vector to advertise to neighbours.
        Supports Split Horizon:
        - If loop_prevention is SPLIT_HORIZON and for_neighbour is specified,
          any route whose next hop is for_neighbour is omitted.
        """
        base_vector = self.routing_table.get_vector()

        if for_neighbour is None or self.loop_prevention == LOOP_PREVENTION_NONE:
            return base_vector

        for_neighbour = str(for_neighbour)
        outgoing_vector: Dict[str, float] = {}

        for dest, cost in base_vector.items():
            next_hop = self.routing_table.get_next_hop(dest)

            # Split Horizon rule: Do not advertise a route back to its next-hop neighbour
            if self.loop_prevention == LOOP_PREVENTION_SPLIT_HORIZON and next_hop == for_neighbour:
                # Omit this route from the vector sent to for_neighbour
                continue

            outgoing_vector[dest] = cost

        return outgoing_vector


if __name__ == "__main__":
    print("=== Split Horizon Loop Prevention Demo (Commit 05) ===")
    print("Scenario: R1 --- (cost 2) --- R2 --- (cost 3) --- R3")
    print("R1 routes traffic to R3 THROUGH next-hop R2.")

    # Initialize R1 with Split Horizon enabled
    node_r1 = DistanceVectorNode(
        router_id="R1",
        neighbours={"R2": 2.0, "Other": 10.0},
        loop_prevention=LOOP_PREVENTION_SPLIT_HORIZON
    )

    # R1 learns route to R3 via R2
    node_r1.receive_vector("R2", {"R2": 0.0, "R3": 3.0})

    print("\nR1 Routing Table:")
    node_r1.routing_table.display()

    print("\n1. Vector R1 advertises to 'Other' (which is NOT the next hop):")
    vector_for_other = node_r1.get_outgoing_vector(for_neighbour="Other")
    print(" ", vector_for_other)

    print("\n2. Vector R1 advertises to 'R2' (which IS the next hop for R3):")
    vector_for_r2 = node_r1.get_outgoing_vector(for_neighbour="R2")
    print(" ", vector_for_r2)

    print("\nNotice: R3 is omitted from the vector sent to R2 because R1 learned R3 via R2!")
    print("Visible result: Split Horizon omits routes learned from that neighbour!")
