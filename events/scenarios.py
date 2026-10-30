"""
Demonstration Scenarios for Network Anomalies:
1. Transient Forwarding Loops
2. Routing Black Holes
3. Link Flapping Storms
Part of Distributed Routing Protocols Project.
"""

import sys
import os
from typing import Dict, List, Tuple

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from algorithms.path_vector import PathVectorRouter
from events.event_engine import EventEngine, NetworkEvent
from visualization.convergence import ConvergenceTracker


class AnomalyScenarios:
    """Demonstrates and analyzes transient loops, black holes, and link flapping."""

    def __init__(self):
        self.engine = EventEngine()
        self.tracker = ConvergenceTracker()

    def run_transient_loop_demo(self) -> Tuple[bool, List[str]]:
        """
        Demonstration 1: Transient Forwarding Loop
        Simulates an inconsistent transient state where Router A points to B
        and Router B points to A for destination D.
        """
        print("\n" + "=" * 65)
        print("  SCENARIO 1: Transient Forwarding Loop Demonstration")
        print("=" * 65)

        # Inconsistent intermediate state:
        transient_tables = {
            "A": {"D": {"next_hop": "B", "cost": 4.0}},
            "B": {"D": {"next_hop": "A", "cost": 5.0}},
            "C": {"D": {"next_hop": "D", "cost": 1.0}},
            "D": {"D": {"next_hop": "D", "cost": 0.0}}
        }

        print("State: Link failure occurred, but updates are mid-flight.")
        print("  Router A routing table -> Destination D via Next Hop 'B'")
        print("  Router B routing table -> Destination D via Next Hop 'A'")

        has_loop, trace = self.tracker.detect_forwarding_loop(transient_tables, source="A", destination="D")
        loop_str = " -> ".join(trace)
        print(f"\n[Forwarding Trace] Packet path: {loop_str}")
        print(f"[Loop Detected] {has_loop} (Cycle identified: {trace[-2]} <-> {trace[-1]})")
        print("Resolution: Path Vector loop detection rejects paths containing self, breaking the loop.")
        return has_loop, trace

    def run_black_hole_demo(self) -> Tuple[bool, str]:
        """
        Demonstration 2: Routing Black Hole
        Router D crashes, but Router A hasn't yet processed the withdrawal.
        Packets sent towards D reach a dead end and get silently dropped.
        """
        print("\n" + "=" * 65)
        print("  SCENARIO 2: Routing Black Hole Demonstration")
        print("=" * 65)

        routers = {
            "A": PathVectorRouter("A", {"B": 2.0, "D": 5.0}),
            "B": PathVectorRouter("B", {"A": 2.0, "C": 3.0}),
            "C": PathVectorRouter("C", {"B": 3.0, "D": 1.0}),
            "D": PathVectorRouter("D", {"A": 5.0, "C": 1.0}),
        }

        print("Initial State: Router A has an active route to D.")
        route_before = routers["A"].routing_table.get("D")
        print(f"  A's route to D: Next Hop {route_before.next_hop}, Cost {route_before.cost}")

        # Crash Router D
        print("\n[Event Trigger] ROUTER_CRASH event on Node 'D'")
        event = NetworkEvent(event_type="ROUTER_CRASH", time_offset=1.0, node_a="D")
        self.engine.apply_event(event, routers)

        # Before updates propagate, packets sent from A to D hit a severed link
        packet_dropped = "D" not in routers["A"].neighbours
        print(f"[Black Hole State] Router A attempts to forward to next hop D, but link is DOWN.")
        print(f"[Packet Status] Silently Dropped: {packet_dropped} (Black Hole created)")

        # Re-convergence eliminates the black hole
        routers["A"].remove_neighbour("D")
        print(f"[Re-convergence] Router A invalidates dead route. Routing table cleansed.")
        return packet_dropped, "A -> D (Dropped)"

    def run_link_flapping_demo(self, flaps: int = 5) -> int:
        """
        Demonstration 3: Link Flapping
        Simulates an unstable link oscillating between UP and DOWN rapidly,
        measuring the resulting storm of update advertisements.
        """
        print("\n" + "=" * 65)
        print("  SCENARIO 3: Link Flapping Storm Demonstration")
        print("=" * 65)

        routers = {
            "A": PathVectorRouter("A", {"B": 2.0, "D": 5.0}),
            "B": PathVectorRouter("B", {"A": 2.0, "C": 3.0}),
            "C": PathVectorRouter("C", {"B": 3.0, "D": 1.0}),
            "D": PathVectorRouter("D", {"A": 5.0, "C": 1.0}),
        }

        total_updates_triggered = 0

        print(f"Simulating {flaps} rapid UP/DOWN cycles on link A <-> B...")
        for i in range(1, flaps + 1):
            # Flap DOWN
            down_event = NetworkEvent(event_type="LINK_DOWN", time_offset=float(i), node_a="A", node_b="B")
            self.engine.apply_event(down_event, routers)
            total_updates_triggered += len(routers["A"].neighbours) + len(routers["B"].neighbours)

            # Flap UP
            up_event = NetworkEvent(event_type="LINK_UP", time_offset=float(i) + 0.5, node_a="A", node_b="B", new_cost=2.0)
            self.engine.apply_event(up_event, routers)
            total_updates_triggered += len(routers["A"].neighbours) + len(routers["B"].neighbours)

            print(f"  Flap Cycle {i}: Link A-B toggled DOWN then UP -> {total_updates_triggered} cumulative update messages.")

        print(f"\n[Observation] {flaps} physical link flaps generated {total_updates_triggered} route update messages!")
        print("In production networks (BGP/OSPF), 'Route Flap Damping' is required to penalize flapping links.")
        return total_updates_triggered


if __name__ == "__main__":
    demo = AnomalyScenarios()
    demo.run_transient_loop_demo()
    demo.run_black_hole_demo()
    demo.run_link_flapping_demo()
