"""
Routing Table Module for Distributed Routing Protocols.
Stores destination routes, costs (metrics), next hops, and update timestamps.
"""

import time
from typing import Dict, List, Optional, Any


class RouteEntry:
    """Represents a single route entry in the routing table."""

    def __init__(
        self,
        destination: str,
        cost: float,
        next_hop: str,
        last_updated: Optional[float] = None
    ):
        self.destination = str(destination)
        self.cost = float(cost)
        self.next_hop = str(next_hop)
        self.last_updated = last_updated if last_updated is not None else time.time()

    def update(self, cost: float, next_hop: str, timestamp: Optional[float] = None) -> bool:
        """
        Updates the route's cost and next hop.
        Returns True if the cost or next hop actually changed.
        """
        cost = float(cost)
        next_hop = str(next_hop)
        changed = (self.cost != cost or self.next_hop != next_hop)
        self.cost = cost
        self.next_hop = next_hop
        self.last_updated = timestamp if timestamp is not None else time.time()
        return changed

    def __repr__(self) -> str:
        return (
            f"RouteEntry(destination='{self.destination}', "
            f"cost={self.cost}, next_hop='{self.next_hop}', "
            f"last_updated={self.last_updated:.2f})"
        )


class RoutingTable:
    """
    Routing table maintained by each router.
    Stores and manages routes indexed by destination router ID.
    """

    def __init__(self, owner_id: str):
        self.owner_id = str(owner_id)
        self._table: Dict[str, RouteEntry] = {}
        # Route to self always has cost 0, next_hop = owner_id
        self.update_route(self.owner_id, cost=0.0, next_hop=self.owner_id)

    def update_route(
        self,
        destination: str,
        cost: float,
        next_hop: str,
        timestamp: Optional[float] = None
    ) -> bool:
        """
        Stores or updates a route to destination.
        Returns True if a new route was added or an existing route changed.
        """
        destination = str(destination)
        cost = float(cost)
        next_hop = str(next_hop)

        if destination in self._table:
            return self._table[destination].update(cost, next_hop, timestamp)

        self._table[destination] = RouteEntry(
            destination=destination,
            cost=cost,
            next_hop=next_hop,
            last_updated=timestamp
        )
        return True

    def get_route(self, destination: str) -> Optional[RouteEntry]:
        """Retrieves the RouteEntry for a destination, or None if not present."""
        return self._table.get(destination)

    def get_cost(self, destination: str) -> float:
        """Returns the cost to destination, or float('inf') if unreachable/unknown."""
        route = self._table.get(destination)
        return route.cost if route is not None else float("inf")

    def get_next_hop(self, destination: str) -> Optional[str]:
        """Returns the next hop router ID for destination, or None if unknown."""
        route = self._table.get(destination)
        return route.next_hop if route is not None else None

    def has_route(self, destination: str) -> bool:
        """Checks if a route exists for the destination."""
        return destination in self._table

    def remove_route(self, destination: str) -> bool:
        """Removes a destination from the routing table. Returns True if removed."""
        if destination in self._table:
            del self._table[destination]
            return True
        return False

    def get_all_destinations(self) -> List[str]:
        """Returns a sorted list of all known destination IDs."""
        return sorted(self._table.keys())

    def __len__(self) -> int:
        return len(self._table)

    def __contains__(self, destination: str) -> bool:
        return destination in self._table

    def __repr__(self) -> str:
        return f"RoutingTable(owner='{self.owner_id}', routes={list(self._table.values())})"


if __name__ == "__main__":
    print(f"=== Routing Table Demonstration (Commit 01) ===")
    table = RoutingTable(owner_id="R1")
    print(f"Initialized table for {table.owner_id}:")
    print(" ", table.get_route("R1"))

    print("\n1. Storing routes to R2 and R3:")
    table.update_route("R2", cost=2.0, next_hop="R2")
    table.update_route("R3", cost=5.0, next_hop="R2")
    print("  R2 ->", table.get_route("R2"))
    print("  R3 ->", table.get_route("R3"))

    print("\n2. Retrieving route attributes:")
    print(f"  Cost to R3: {table.get_cost('R3')}")
    print(f"  Next hop to R3: {table.get_next_hop('R3')}")

    print("\n3. Updating route to R3 (cheaper path via R2 discovered):")
    time.sleep(0.05)
    changed = table.update_route("R3", cost=3.0, next_hop="R2")
    print(f"  Route changed: {changed}")
    print("  Updated R3 ->", table.get_route("R3"))
    print(f"  New Cost to R3: {table.get_cost('R3')}")
    print("\nVisible result: Route successfully stored, updated, and retrieved!")
