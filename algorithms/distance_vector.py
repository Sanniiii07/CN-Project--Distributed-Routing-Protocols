"""
Distance Vector Routing Protocol Implementation.
Uses the Bellman-Ford algorithm to compute shortest paths based on
distance vectors received from direct neighbours.
"""

import os
import sys
from typing import Dict, List, Optional, Set

# Ensure project root is accessible for imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from router.routing_table import RoutingTable


class DistanceVectorNode:
    """
    A Distance Vector routing engine for a single router.
    Calculates candidate route costs using the Bellman-Ford equation:
      D_x(y) = min_v { c(x, v) + D_v(y) }
    """

    def __init__(self, router_id: str, neighbours: Optional[Dict[str, float]] = None):
        self.router_id = str(router_id)
        # Direct link costs to neighbours: {neighbour_id: link_cost}
        self.neighbours: Dict[str, float] = {}
        if neighbours:
            for nbr, cost in neighbours.items():
                self.neighbours[str(nbr)] = float(cost)

        # Main routing table: stores best known cost and next hop
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

    def receive_vector(self, neighbour_id: str, vector: Dict[str, float]) -> bool:
        """
        Receives a distance vector advertised by a direct neighbour.
        Stores the vector and recalculates routes.
        Returns True if any route in the local routing table changed.
        """
        neighbour_id = str(neighbour_id)
        if neighbour_id not in self.neighbours:
            # Only process vectors from direct active neighbours
            return False

        # Store a copy of the received vector
        self.neighbour_vectors[neighbour_id] = {
            str(dest): float(cost) for dest, cost in vector.items()
        }

        # Recalculate routes using the new information
        return self.recalculate_routes()

    def recalculate_routes(self) -> bool:
        """
        Runs the Bellman-Ford calculation across all known destinations:
          D_x(y) = min_v { c(x, v) + D_v(y) }
        Returns True if the routing table changed.
        """
        changed = False

        # Gather all known destinations: self, direct neighbours, and destinations in vectors
        all_destinations: Set[str] = {self.router_id}
        all_destinations.update(self.neighbours.keys())
        for vector in self.neighbour_vectors.values():
            all_destinations.update(vector.keys())

        for dest in all_destinations:
            # Route to self is always cost 0 via self
            if dest == self.router_id:
                if self.routing_table.get_cost(dest) != 0.0:
                    self.routing_table.update_route(dest, cost=0.0, next_hop=self.router_id)
                    changed = True
                continue

            # Find the cheapest candidate path across all active neighbours
            best_cost = float("inf")
            best_next_hop: Optional[str] = None

            # Option 1: Direct link (if destination is a direct neighbour)
            if dest in self.neighbours:
                best_cost = self.neighbours[dest]
                best_next_hop = dest

            # Option 2: Paths via each neighbour v using Bellman-Ford
            for nbr, link_cost in self.neighbours.items():
                nbr_vector = self.neighbour_vectors.get(nbr, {})
                if dest in nbr_vector:
                    candidate_cost = link_cost + nbr_vector[dest]
                    if candidate_cost < best_cost:
                        best_cost = candidate_cost
                        best_next_hop = nbr

            # Update routing table if we found a route and it changed
            if best_next_hop is not None and best_cost != float("inf"):
                old_cost = self.routing_table.get_cost(dest)
                old_hop = self.routing_table.get_next_hop(dest)
                if old_cost != best_cost or old_hop != best_next_hop:
                    self.routing_table.update_route(dest, cost=best_cost, next_hop=best_next_hop)
                    changed = True

        return changed

    def get_outgoing_vector(self) -> Dict[str, float]:
        """
        Returns the Distance Vector to advertise to neighbours.
        Basic version: advertises all destinations and their best costs.
        """
        return self.routing_table.get_vector()


if __name__ == "__main__":
    print("=== Distance Vector Calculation Demo (Commit 03) ===")
    print("Scenario: R1 is connected to R2 (cost 2) and R3 (expensive direct link cost 10).")
    print("R2 is connected to R3 (cheap link cost 1).")

    # Step 1: Initialize R1 with initial direct link costs
    node_r1 = DistanceVectorNode(router_id="R1", neighbours={"R2": 2.0, "R3": 10.0})
    print("\nInitial routing table at R1 (before receiving R2's vector):")
    node_r1.routing_table.display()

    # Step 2: R2 discovers it can reach R3 with cost 1, and advertises its vector to R1
    r2_vector = {"R2": 0.0, "R3": 1.0}
    print(f"\nR1 receives distance vector from R2: {r2_vector}")

    # Step 3: R1 processes R2's vector
    table_changed = node_r1.receive_vector("R2", r2_vector)
    print(f"Routing table changed: {table_changed}")

    print("\nUpdated routing table at R1 (cheaper route chosen):")
    node_r1.routing_table.display()

    # Verify the result
    cost_to_r3 = node_r1.routing_table.get_cost("R3")
    hop_to_r3 = node_r1.routing_table.get_next_hop("R3")
    print(f"\nVisible result: Cost to R3 improved from 10 to {cost_to_r3} via next hop '{hop_to_r3}'!")
