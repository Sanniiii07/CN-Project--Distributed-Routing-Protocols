"""
Unit Tests for Distance Vector Routing and Loop Prevention.
Tests route updates, route withdrawal, Split Horizon, Poisoned Reverse,
and the Count-to-Infinity simulation.
Part of Distributed Routing Protocols Project (P7).
"""

import os
import sys
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from router.routing_table import RoutingTable, RouteEntry, INFINITY
from algorithms.distance_vector import (
    DistanceVectorNode,
    LOOP_PREVENTION_NONE,
    LOOP_PREVENTION_SPLIT_HORIZON,
    LOOP_PREVENTION_POISONED_REVERSE,
)
from experiments.count_to_infinity import simulate_count_to_infinity


class TestRoutingTable(unittest.TestCase):
    """Tests for RoutingTable and RouteEntry data structures."""

    def setUp(self):
        self.table = RoutingTable(owner_id="R1")

    def test_self_route_initialized(self):
        """Owner should have cost 0 to itself."""
        self.assertEqual(self.table.get_cost("R1"), 0.0)
        self.assertEqual(self.table.get_next_hop("R1"), "R1")

    def test_update_and_retrieve_route(self):
        """Routes can be added, updated, and retrieved with next hop."""
        self.table.update_route("R2", cost=2.0, next_hop="R2")
        self.assertEqual(self.table.get_cost("R2"), 2.0)
        self.assertEqual(self.table.get_next_hop("R2"), "R2")

        # Update route with cheaper cost
        changed = self.table.update_route("R2", cost=1.0, next_hop="R3")
        self.assertTrue(changed)
        self.assertEqual(self.table.get_cost("R2"), 1.0)
        self.assertEqual(self.table.get_next_hop("R2"), "R3")

    def test_unreachable_destination(self):
        """Marking a route unreachable sets cost to INFINITY (16)."""
        self.table.update_route("R3", cost=4.0, next_hop="R2")
        self.assertTrue(self.table.is_reachable("R3"))

        self.table.mark_unreachable("R3")
        self.assertFalse(self.table.is_reachable("R3"))
        self.assertEqual(self.table.get_cost("R3"), INFINITY)
        self.assertIsNone(self.table.get_next_hop("R3"))

    def test_serialization(self):
        """Routing table converts properly to vector dictionary and JSON."""
        self.table.update_route("R2", cost=2.0, next_hop="R2")
        vector = self.table.get_vector()
        self.assertEqual(vector["R1"], 0.0)
        self.assertEqual(vector["R2"], 2.0)

        data = self.table.to_dict()
        self.assertEqual(data["owner_id"], "R1")
        self.assertIn("R2", data["routes"])


class TestDistanceVector(unittest.TestCase):
    """Tests for Distance Vector routing calculations and loop prevention."""

    def test_bellman_ford_cheaper_route(self):
        """Cost improves when a cheaper route via a neighbour is received."""
        # R1 connected to R2 (cost 2) and R3 (cost 10)
        node = DistanceVectorNode("R1", neighbours={"R2": 2.0, "R3": 10.0})
        self.assertEqual(node.routing_table.get_cost("R3"), 10.0)

        # R2 advertises C(R2->R3) = 1.0
        # Total cost via R2 = 2.0 + 1.0 = 3.0 (better than 10.0)
        changed = node.receive_vector("R2", {"R2": 0.0, "R3": 1.0})
        self.assertTrue(changed)
        self.assertEqual(node.routing_table.get_cost("R3"), 3.0)
        self.assertEqual(node.routing_table.get_next_hop("R3"), "R2")

    def test_link_failure_handling(self):
        """Failing a link marks affected destinations as unreachable."""
        node = DistanceVectorNode("R1", neighbours={"R2": 2.0})
        node.receive_vector("R2", {"R2": 0.0, "R3": 3.0})
        self.assertEqual(node.routing_table.get_cost("R3"), 5.0)

        # Link to R2 goes down
        node.fail_link("R2")
        self.assertEqual(node.routing_table.get_cost("R2"), INFINITY)
        self.assertEqual(node.routing_table.get_cost("R3"), INFINITY)
        self.assertFalse(node.routing_table.is_reachable("R3"))

    def test_split_horizon(self):
        """Split Horizon omits routes from the vector sent back to next-hop neighbour."""
        node = DistanceVectorNode(
            "R1",
            neighbours={"R2": 2.0, "R4": 5.0},
            loop_prevention=LOOP_PREVENTION_SPLIT_HORIZON
        )
        # Learn route to R3 via R2
        node.receive_vector("R2", {"R2": 0.0, "R3": 1.0})
        self.assertEqual(node.routing_table.get_next_hop("R3"), "R2")

        # Vector sent to R2 should OMIT R3
        vec_for_r2 = node.get_outgoing_vector(for_neighbour="R2")
        self.assertNotIn("R3", vec_for_r2)

        # Vector sent to R4 should INCLUDE R3
        vec_for_r4 = node.get_outgoing_vector(for_neighbour="R4")
        self.assertIn("R3", vec_for_r4)
        self.assertEqual(vec_for_r4["R3"], 3.0)

    def test_poisoned_reverse(self):
        """Poisoned Reverse advertises next-hop routes with metric INFINITY (16)."""
        node = DistanceVectorNode(
            "R1",
            neighbours={"R2": 2.0, "R4": 5.0},
            loop_prevention=LOOP_PREVENTION_POISONED_REVERSE
        )
        node.receive_vector("R2", {"R2": 0.0, "R3": 1.0})
        self.assertEqual(node.routing_table.get_next_hop("R3"), "R2")

        # Vector sent to R2 should advertise R3 with cost 16 (poisoned)
        vec_for_r2 = node.get_outgoing_vector(for_neighbour="R2")
        self.assertIn("R3", vec_for_r2)
        self.assertEqual(vec_for_r2["R3"], INFINITY)

        # Vector sent to R4 should advertise normal cost
        vec_for_r4 = node.get_outgoing_vector(for_neighbour="R4")
        self.assertEqual(vec_for_r4["R3"], 3.0)

    def test_udp_advertisement_helpers(self):
        """Tests JSON advertisement creation and processing."""
        node = DistanceVectorNode("R1", neighbours={"R2": 2.0})
        ad = node.create_advertisement(for_neighbour="R2")
        self.assertEqual(ad["type"], "DV_UPDATE")
        self.assertEqual(ad["sender"], "R1")
        self.assertIn("vector", ad)

        incoming_ad = {
            "type": "DV_UPDATE",
            "sender": "R2",
            "vector": {"R2": 0.0, "R3": 4.0}
        }
        changed = node.process_advertisement(incoming_ad)
        self.assertTrue(changed)
        self.assertEqual(node.routing_table.get_cost("R3"), 6.0)


class TestCountToInfinity(unittest.TestCase):
    """Tests for the Count-to-Infinity experiment module."""

    def test_count_to_infinity_loop_without_prevention(self):
        """Without loop prevention, failure causes multiple rounds of bouncing metric."""
        res = simulate_count_to_infinity(mode=LOOP_PREVENTION_NONE)
        # Takes multiple rounds (7 rounds) to bounce up to 16
        self.assertGreater(res["rounds"], 1)
        self.assertTrue(res["converged"])

    def test_split_horizon_prevents_loop(self):
        """Split Horizon converges in 1 round after failure."""
        res = simulate_count_to_infinity(mode=LOOP_PREVENTION_SPLIT_HORIZON)
        self.assertEqual(res["rounds"], 1)
        self.assertTrue(res["converged"])

    def test_poisoned_reverse_prevents_loop(self):
        """Poisoned Reverse converges in 1 round after failure."""
        res = simulate_count_to_infinity(mode=LOOP_PREVENTION_POISONED_REVERSE)
        self.assertEqual(res["rounds"], 1)
        self.assertTrue(res["converged"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
