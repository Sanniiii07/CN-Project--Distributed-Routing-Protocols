"""
Routing Table Module for Distributed Routing Protocols.
Stores destination routes, costs (metrics), next hops, and update timestamps.
Supports clean table display, JSON serialization, and unreachable route handling.
"""

import json
import time
from typing import Dict, List, Optional, Any

# Standard routing metric infinity (RIP convention: 16 is unreachable)
INFINITY: float = 16.0


class RouteEntry:
    """Represents a single route entry in the routing table."""

    def __init__(
        self,
        destination: str,
        cost: float,
        next_hop: Optional[str],
        last_updated: Optional[float] = None
    ):
        self.destination = str(destination)
        self.cost = float(cost)
        self.next_hop = str(next_hop) if next_hop is not None else None
        self.last_updated = last_updated if last_updated is not None else time.time()

    def update(self, cost: float, next_hop: Optional[str], timestamp: Optional[float] = None) -> bool:
        """
        Updates the route's cost and next hop.
        Returns True if the cost or next hop actually changed.
        """
        cost = float(cost)
        next_hop_str = str(next_hop) if next_hop is not None else None
        changed = (self.cost != cost or self.next_hop != next_hop_str)
        self.cost = cost
        self.next_hop = next_hop_str
        self.last_updated = timestamp if timestamp is not None else time.time()
        return changed

    def is_reachable(self) -> bool:
        """Returns True if the destination is reachable (cost < INFINITY)."""
        return self.cost < INFINITY

    def to_dict(self) -> dict:
        """Returns the route entry as a dictionary."""
        return {
            "destination": self.destination,
            "cost": self.cost if self.cost < INFINITY else "INF",
            "next_hop": self.next_hop,
            "reachable": self.is_reachable(),
            "last_updated": round(self.last_updated, 2)
        }

    def __repr__(self) -> str:
        cost_display = f"{self.cost:.1f}" if self.cost < INFINITY else "INF"
        return (
            f"RouteEntry(destination='{self.destination}', "
            f"cost={cost_display}, next_hop='{self.next_hop}', "
            f"reachable={self.is_reachable()})"
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
        next_hop: Optional[str],
        timestamp: Optional[float] = None
    ) -> bool:
        """
        Stores or updates a route to destination.
        Returns True if a new route was added or an existing route changed.
        """
        destination = str(destination)
        cost = float(cost)
        next_hop_str = str(next_hop) if next_hop is not None else None

        if destination in self._table:
            return self._table[destination].update(cost, next_hop_str, timestamp)

        self._table[destination] = RouteEntry(
            destination=destination,
            cost=cost,
            next_hop=next_hop_str,
            last_updated=timestamp
        )
        return True

    def mark_unreachable(self, destination: str, timestamp: Optional[float] = None) -> bool:
        """Marks a destination as unreachable (cost = INFINITY, next_hop = None)."""
        return self.update_route(destination, cost=INFINITY, next_hop=None, timestamp=timestamp)

    def is_reachable(self, destination: str) -> bool:
        """Returns True if destination is known and has cost < INFINITY."""
        route = self._table.get(destination)
        return route is not None and route.is_reachable()

    def get_route(self, destination: str) -> Optional[RouteEntry]:
        """Retrieves the RouteEntry for a destination, or None if not present."""
        return self._table.get(destination)

    def get_cost(self, destination: str) -> float:
        """Returns the cost to destination, or INFINITY if unreachable/unknown."""
        route = self._table.get(destination)
        return route.cost if route is not None else INFINITY

    def get_next_hop(self, destination: str) -> Optional[str]:
        """Returns the next hop router ID for destination, or None if unknown/unreachable."""
        route = self._table.get(destination)
        return route.next_hop if route is not None else None

    def has_route(self, destination: str) -> bool:
        """Checks if a route entry exists for the destination."""
        return destination in self._table

    def remove_route(self, destination: str) -> bool:
        """Removes a destination from the routing table completely."""
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
        Destinations with cost >= INFINITY are capped at INFINITY.
        """
        return {
            dest: (entry.cost if entry.cost < INFINITY else INFINITY)
            for dest, entry in self._table.items()
        }

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
        print(f"{'Destination':<14} {'Cost':<12} {'Next Hop':<12} {'Status':<14}")
        print("-" * 52)
        for dest in self.get_all_destinations():
            entry = self._table[dest]
            if entry.cost >= INFINITY:
                cost_str = f"{int(INFINITY)} (INF)"
                hop_str = "-"
                status_str = "UNREACHABLE"
            else:
                cost_str = str(int(entry.cost)) if entry.cost.is_integer() else f"{entry.cost:.1f}"
                hop_str = entry.next_hop if entry.next_hop else "-"
                status_str = "REACHABLE"
            print(f"{dest:<14} {cost_str:<12} {hop_str:<12} {status_str:<14}")
        print("-" * 52)

    def __len__(self) -> int:
        return len(self._table)

    def __contains__(self, destination: str) -> bool:
        return destination in self._table

    def __repr__(self) -> str:
        return f"RoutingTable(owner='{self.owner_id}', routes={list(self._table.values())})"
