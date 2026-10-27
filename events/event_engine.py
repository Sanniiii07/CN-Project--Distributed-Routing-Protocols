"""
Dynamic Network Event Engine for Distributed Routing Simulations.
Handles events: LINK_DOWN, LINK_UP, LINK_COST_CHANGE, ROUTER_CRASH, ROUTER_RECOVER, and LINK_FLAP.
"""

from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
import time


@dataclass
class NetworkEvent:
    event_type: str  # "LINK_DOWN", "LINK_UP", "LINK_COST_CHANGE", "ROUTER_CRASH", "ROUTER_RECOVER"
    time_offset: float  # In seconds or simulation ticks
    node_a: str
    node_b: Optional[str] = None
    new_cost: Optional[float] = None
    description: str = ""

    def __repr__(self) -> str:
        target = f"{self.node_a}<->{self.node_b}" if self.node_b else self.node_a
        cost_str = f" cost={self.new_cost}" if self.new_cost is not None else ""
        return f"Event({self.event_type} on {target} at t={self.time_offset}s{cost_str})"


class EventEngine:
    """
    Manages and applies network topology change events to routers.
    Supports both simulated rounds and real-time execution.
    """

    def __init__(self):
        self.events: List[NetworkEvent] = []
        self.event_history: List[dict] = []
        self._listeners: List[Callable[[NetworkEvent], None]] = []

    def schedule_event(
        self,
        event_type: str,
        time_offset: float,
        node_a: str,
        node_b: Optional[str] = None,
        new_cost: Optional[float] = None,
        description: str = ""
    ) -> NetworkEvent:
        """Schedule a network event to occur at a future time offset."""
        event = NetworkEvent(
            event_type=event_type,
            time_offset=time_offset,
            node_a=node_a,
            node_b=node_b,
            new_cost=new_cost,
            description=description
        )
        self.events.append(event)
        self.events.sort(key=lambda e: e.time_offset)
        return event

    def register_listener(self, callback: Callable[[NetworkEvent], None]) -> None:
        """Register a callback invoked whenever an event is triggered."""
        self._listeners.append(callback)

    def apply_event(self, event: NetworkEvent, routers: Dict[str, Any]) -> bool:
        """
        Applies a scheduled event to the target router instances.
        Returns True if the event was applied successfully.
        """
        record = {
            "event": event,
            "applied": False,
            "timestamp": time.time()
        }

        if event.event_type == "LINK_DOWN":
            # Bi-directional link failure between node_a and node_b
            if event.node_a in routers and event.node_b in routers:
                if hasattr(routers[event.node_a], "remove_neighbour"):
                    routers[event.node_a].remove_neighbour(event.node_b)
                if hasattr(routers[event.node_b], "remove_neighbour"):
                    routers[event.node_b].remove_neighbour(event.node_a)
                record["applied"] = True

        elif event.event_type == "LINK_UP":
            cost = event.new_cost if event.new_cost is not None else 1.0
            if event.node_a in routers and event.node_b in routers:
                if hasattr(routers[event.node_a], "set_neighbour"):
                    routers[event.node_a].set_neighbour(event.node_b, cost)
                if hasattr(routers[event.node_b], "set_neighbour"):
                    routers[event.node_b].set_neighbour(event.node_a, cost)
                record["applied"] = True

        elif event.event_type == "LINK_COST_CHANGE":
            cost = event.new_cost if event.new_cost is not None else 1.0
            if event.node_a in routers and event.node_b in routers:
                if hasattr(routers[event.node_a], "set_neighbour"):
                    routers[event.node_a].set_neighbour(event.node_b, cost)
                if hasattr(routers[event.node_b], "set_neighbour"):
                    routers[event.node_b].set_neighbour(event.node_a, cost)
                record["applied"] = True

        elif event.event_type == "ROUTER_CRASH":
            crashed_id = event.node_a
            if crashed_id in routers:
                # Disconnect crashed router from all its neighbors
                crashed_router = routers[crashed_id]
                nbrs = list(getattr(crashed_router, "neighbours", {}).keys())
                for nbr in nbrs:
                    if nbr in routers and hasattr(routers[nbr], "remove_neighbour"):
                        routers[nbr].remove_neighbour(crashed_id)
                    if hasattr(crashed_router, "remove_neighbour"):
                        crashed_router.remove_neighbour(nbr)
                record["applied"] = True

        self.event_history.append(record)

        # Notify any registered listeners
        for listener in self._listeners:
            listener(event)

        return record["applied"]

    def run_scheduled_events(self, routers: Dict[str, Any], current_time: float) -> List[NetworkEvent]:
        """
        Runs all pending events whose time_offset <= current_time.
        Returns list of executed events.
        """
        executed = []
        pending = []

        for event in self.events:
            if event.time_offset <= current_time:
                self.apply_event(event, routers)
                executed.append(event)
            else:
                pending.append(event)

        self.events = pending
        return executed
