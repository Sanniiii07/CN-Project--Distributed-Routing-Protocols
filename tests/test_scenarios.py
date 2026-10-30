"""
Unit tests for network anomaly scenarios (loops, black holes, flapping).
"""

import unittest
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from events.scenarios import AnomalyScenarios


class TestAnomalyScenarios(unittest.TestCase):

    def setUp(self):
        self.scenarios = AnomalyScenarios()

    def test_transient_forwarding_loop_detection(self):
        has_loop, trace = self.scenarios.run_transient_loop_demo()
        self.assertTrue(has_loop)
        self.assertIn("A", trace)
        self.assertIn("B", trace)

    def test_black_hole_demonstration(self):
        packet_dropped, status = self.scenarios.run_black_hole_demo()
        self.assertTrue(packet_dropped)
        self.assertIn("Dropped", status)

    def test_link_flapping_message_explosion(self):
        update_count = self.scenarios.run_link_flapping_demo(flaps=3)
        self.assertGreater(update_count, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
