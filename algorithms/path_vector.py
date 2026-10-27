"""
Path Vector Routing Protocol Implementation with Loop Detection.
Part of Distributed Routing Protocols Project.
"""

from typing import Dict, List, Optional, Tuple


class RouteEntry:
    def __init__(self, destination: str, next_hop: str, path: List[str], cost: float):
        self.destination = destination
        self.next_hop = next_hop
        self.path = list(path)
        self.cost = cost

    def to_dict(self) -> dict:
        return {
            "destination": self.destination,
            "next_hop": self.next_hop,
            "path": list(self.path),
            "cost": self.cost,
        }

    def __repr__(self) -> str:
        path_str = " -> ".join(self.path)
        return f"Route(dest={self.destination}, next_hop={self.next_hop}, path=[{path_str}], cost={self.cost})"


class PathVectorRouter:
    """
    Implements a Path Vector routing node.
    Each router maintains:
      - router_id: identifier (e.g. 'A', 'B', etc.)
      - neighbours: mapping neighbor_id -> link_cost
      - routing_table: mapping destination -> RouteEntry
    """

    def __init__(self, router_id: str, neighbours: Optional[Dict[str, float]] = None):
        self.router_id = router_id
        self.neighbours: Dict[str, float] = dict(neighbours) if neighbours else {}
        self.routing_table: Dict[str, RouteEntry] = {}

        # Add self-route (cost 0, path [self])
        self.routing_table[router_id] = RouteEntry(
            destination=router_id,
            next_hop=router_id,
            path=[router_id],
            cost=0.0
        )

        # Initialize direct neighbor routes
        for nbr, cost in self.neighbours.items():
            self.routing_table[nbr] = RouteEntry(
                destination=nbr,
                next_hop=nbr,
                path=[self.router_id, nbr],
                cost=float(cost)
            )

    def set_neighbour(self, neighbour_id: str, cost: float) -> None:
        """Add or update a direct neighbor link."""
        self.neighbours[neighbour_id] = float(cost)
        self.routing_table[neighbour_id] = RouteEntry(
            destination=neighbour_id,
            next_hop=neighbour_id,
            path=[self.router_id, neighbour_id],
            cost=float(cost)
        )

    def remove_neighbour(self, neighbour_id: str) -> None:
        """Handle link failure or removal of neighbor."""
        if neighbour_id in self.neighbours:
            del self.neighbours[neighbour_id]

        # Invalidate any route that depended on this neighbour as next_hop
        to_delete = [
            dest for dest, route in self.routing_table.items()
            if route.next_hop == neighbour_id and dest != self.router_id
        ]
        for dest in to_delete:
            del self.routing_table[dest]

    def create_advertisement(self) -> dict:
        """
        Creates the Path Vector update message to send to neighbors.
        Format:
        {
            "type": "PV_UPDATE",
            "sender": router_id,
            "routes": {
                dest: {"path": [...], "cost": ...}
            }
        }
        """
        routes_payload = {}
        for dest, entry in self.routing_table.items():
            routes_payload[dest] = {
                "path": list(entry.path),
                "cost": entry.cost
            }
        return {
            "type": "PV_UPDATE",
            "sender": self.router_id,
            "routes": routes_payload
        }

    def process_advertisement(self, sender: str, routes_payload: Dict[str, dict]) -> bool:
        """
        Process incoming Path Vector update from a neighbor.
        Applies loop detection:
          - If self.router_id is already in route["path"], REJECT (prevents loops).
        Returns True if routing table changed, False otherwise.
        """
        if sender not in self.neighbours:
            # Not a recognized or active direct neighbor
            return False

        link_cost = self.neighbours[sender]
        changed = False

        for dest, route_info in routes_payload.items():
            path = route_info.get("path", [])
            advertised_cost = route_info.get("cost", float("inf"))

            # LOOP DETECTION: Reject route if our own ID is present in the path
            if self.router_id in path:
                continue

            new_cost = link_cost + advertised_cost
            new_path = [self.router_id] + path

            # Evaluate candidate route against current table
            current_entry = self.routing_table.get(dest)

            # Update conditions:
            # 1. No route exists yet to this destination
            # 2. Existing route came via the same sender (cost might have updated)
            # 3. New candidate route has strictly lower cost
            if (
                current_entry is None
                or current_entry.next_hop == sender
                or new_cost < current_entry.cost
            ):
                if (
                    current_entry is None
                    or current_entry.cost != new_cost
                    or current_entry.path != new_path
                ):
                    self.routing_table[dest] = RouteEntry(
                        destination=dest,
                        next_hop=sender,
                        path=new_path,
                        cost=new_cost
                    )
                    changed = True

        return changed

    def print_routing_table(self) -> None:
        """Pretty-prints current Path Vector routing table."""
        print(f"\n--- Path Vector Routing Table: Router {self.router_id} ---")
        print(f"{'Destination':<14}{'Next Hop':<12}{'Cost':<8}{'Path'}")
        print("-" * 50)
        for dest in sorted(self.routing_table.keys()):
            entry = self.routing_table[dest]
            path_str = " -> ".join(entry.path)
            cost_str = f"{int(entry.cost)}" if entry.cost.is_integer() else f"{entry.cost:.1f}"
            print(f"{dest:<14}{entry.next_hop:<12}{cost_str:<8}{path_str}")
        print("-" * 50)
