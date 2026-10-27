"""
Unit tests for Event Engine and Convergence Visualization.
"""

import unittest
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from algorithms.path_vector import PathVectorRouter
from events.event_engine import EventEngine, NetworkEvent
from visualization.convergence import ConvergenceTracker


class TestEventEngineAndVisualization(unittest.TestCase):

    def setUp(self):
        self.routers = {
            "A": PathVectorRouter("A", {"B": 2.0, "D": 5.0}),
            "B": PathVectorRouter("B", {"A": 2.0, "C": 3.0}),
            "C": PathVectorRouter("C", {"B": 3.0, "D": 1.0}),
            "D": PathVectorRouter("D", {"A": 5.0, "C": 1.0}),
        }
        self.engine = EventEngine()
        self.tracker = ConvergenceTracker()

    def test_link_down_event_application(self):
        """Verify that a LINK_DOWN event removes neighbor connectivity on both ends."""
        event = NetworkEvent(
            event_type="LINK_DOWN",
            time_offset=1.0,
            node_a="A",
            node_b="B"
        )
        applied = self.engine.apply_event(event, self.routers)
        self.assertTrue(applied)
        self.assertNotIn("B", self.routers["A"].neighbours)
        self.assertNotIn("A", self.routers["B"].neighbours)

    def test_link_cost_change_event(self):
        """Verify that a LINK_COST_CHANGE updates neighbor link weights."""
        event = NetworkEvent(
            event_type="LINK_COST_CHANGE",
            time_offset=2.0,
            node_a="A",
            node_b="B",
            new_cost=10.0
        )
        applied = self.engine.apply_event(event, self.routers)
        self.assertTrue(applied)
        self.assertEqual(self.routers["A"].neighbours["B"], 10.0)
        self.assertEqual(self.routers["B"].neighbours["A"], 10.0)

    def test_router_crash_event(self):
        """Verify that ROUTER_CRASH disconnects the node from all its peers."""
        event = NetworkEvent(
            event_type="ROUTER_CRASH",
            time_offset=3.0,
            node_a="B"
        )
        applied = self.engine.apply_event(event, self.routers)
        self.assertTrue(applied)
        self.assertNotIn("B", self.routers["A"].neighbours)
        self.assertNotIn("B", self.routers["C"].neighbours)

    def test_forwarding_loop_detection(self):
        """Verify that circular next_hops (e.g. A -> B -> A) are correctly caught as loops."""
        dummy_tables = {
            "A": {"D": {"next_hop": "B"}},
            "B": {"D": {"next_hop": "A"}},
            "D": {"D": {"next_hop": "D"}}
        }
        has_loop, trace = self.tracker.detect_forwarding_loop(dummy_tables, "A", "D")
        self.assertTrue(has_loop)
        self.assertEqual(trace, ["A", "B", "A"])

    def test_convergence_recording(self):
        """Verify that convergence rounds and message counts can be snapshotted."""
        self.tracker.record_round(1, self.routers, message_count=4)
        self.assertEqual(len(self.tracker.snapshots), 1)
        self.assertEqual(self.tracker.snapshots[0]["round"], 1)
        self.assertEqual(self.tracker.snapshots[0]["message_count"], 4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
