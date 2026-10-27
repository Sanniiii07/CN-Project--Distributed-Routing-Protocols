"""
Routing Table Module for Distributed Routing Protocols.
Stores destination routes, costs (metrics), next hops, and update timestamps.
Supports clean table display and JSON serialization for network exchange.
"""

import json
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

    def to_dict(self) -> dict:
        """Returns the route entry as a dictionary."""
        return {
            "destination": self.destination,
            "cost": self.cost,
            "next_hop": self.next_hop,
            "last_updated": round(self.last_updated, 2)
        }

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

    def get_vector(self) -> Dict[str, float]:
        """
        Returns the Distance Vector dictionary {destination: cost}.
        This is the payload advertised to neighbouring routers.
        """
        return {dest: entry.cost for dest, entry in self._table.items()}

    def to_dict(self) -> dict:
        """Converts the full table into a dictionary structure."""
        return {
            "owner_id": self.owner_id,
            "routes": {dest: entry.to_dict() for dest, entry in self._table.items()}
        }

    def to_json(self, indent: int = 2) -> str:
        """Serializes the routing table to a JSON-formatted string."""
        return json.dumps(self.to_dict(), indent=indent)

    def display(self) -> None:
        """Prints the routing table in a clean, human-readable format."""
        print(f"\n--- Routing Table (Router {self.owner_id}) ---")
        print(f"{'Destination':<14} {'Cost':<10} {'Next Hop':<12} {'Age':<10}")
        print("-" * 48)
        now = time.time()
        for dest in self.get_all_destinations():
            entry = self._table[dest]
            cost_str = str(int(entry.cost)) if entry.cost.is_integer() else f"{entry.cost:.1f}"
            age_str = f"{now - entry.last_updated:.1f}s ago"
            print(f"{dest:<14} {cost_str:<10} {entry.next_hop:<12} {age_str:<10}")
        print("-" * 48)

    def __len__(self) -> int:
        return len(self._table)

    def __contains__(self, destination: str) -> bool:
        return destination in self._table

    def __repr__(self) -> str:
        return f"RoutingTable(owner='{self.owner_id}', routes={list(self._table.values())})"


if __name__ == "__main__":
    print("=== Routing Table Display & Serialization (Commit 02) ===")
    table = RoutingTable(owner_id="R1")
    table.update_route("R2", cost=2.0, next_hop="R2")
    table.update_route("R3", cost=5.0, next_hop="R2")
    table.update_route("R4", cost=8.0, next_hop="R2")

    print("\n1. Formatted Table Display:")
    table.display()

    print("\n2. Distance Vector Payload (for sharing with neighbors):")
    vector = table.get_vector()
    print(" ", vector)

    print("\n3. JSON Serialization:")
    print(table.to_json())

    print("\nVisible result: Routing table can be formatted cleanly and serialized for network transmission!")
