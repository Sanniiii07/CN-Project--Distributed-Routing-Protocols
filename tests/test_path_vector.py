"""
Unit tests for Path Vector routing and loop detection.
"""

import unittest
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from algorithms.path_vector import PathVectorRouter


class TestPathVectorRouting(unittest.TestCase):

    def test_direct_neighbor_initialization(self):
        router_a = PathVectorRouter("A", {"B": 2.0, "D": 5.0})
        self.assertIn("A", router_a.routing_table)
        self.assertEqual(router_a.routing_table["A"].cost, 0.0)
        self.assertEqual(router_a.routing_table["A"].path, ["A"])

        self.assertIn("B", router_a.routing_table)
        self.assertEqual(router_a.routing_table["B"].cost, 2.0)
        self.assertEqual(router_a.routing_table["B"].path, ["A", "B"])

    def test_loop_detection_rejects_circular_path(self):
        """
        Verify that if an advertised path contains this router's own ID,
        the route is strictly rejected to prevent loops.
        """
        router_a = PathVectorRouter("A", {"B": 2.0})

        # Neighbor B advertises a path to D that already goes through A: [B, C, A, D]
        malformed_advertisement = {
            "D": {
                "path": ["B", "C", "A", "D"],
                "cost": 10.0
            }
        }

        changed = router_a.process_advertisement("B", malformed_advertisement)
        self.assertFalse(changed)
        self.assertNotIn("D", router_a.routing_table)

    def test_path_vector_convergence_diamond_topology(self):
        """
        Topology:
          A --(2)-- B --(3)-- C --(1)-- D
          |                             |
          +------------(5)--------------+
        """
        routers = {
            "A": PathVectorRouter("A", {"B": 2.0, "D": 5.0}),
            "B": PathVectorRouter("B", {"A": 2.0, "C": 3.0}),
            "C": PathVectorRouter("C", {"B": 3.0, "D": 1.0}),
            "D": PathVectorRouter("D", {"A": 5.0, "C": 1.0}),
        }

        # Simulate message exchanges until convergence
        converged = False
        rounds = 0
        max_rounds = 10

        while not converged and rounds < max_rounds:
            converged = True
            rounds += 1
            # Each router generates an advertisement
            ads = {r_id: r.create_advertisement() for r_id, r in routers.items()}

            # Distribute advertisements to connected neighbors
            for r_id, ad in ads.items():
                for nbr_id in routers[r_id].neighbours:
                    changed = routers[nbr_id].process_advertisement(r_id, ad["routes"])
                    if changed:
                        converged = False

        # Verify router A's route to C: Path [A, B, C] with cost 5.0
        self.assertIn("C", routers["A"].routing_table)
        self.assertEqual(routers["A"].routing_table["C"].path, ["A", "B", "C"])
        self.assertEqual(routers["A"].routing_table["C"].cost, 5.0)

        # Verify router A's route to D: Direct link A-D is cost 5, path [A, D]
        self.assertIn("D", routers["A"].routing_table)
        self.assertEqual(routers["A"].routing_table["D"].cost, 5.0)
        self.assertEqual(routers["A"].routing_table["D"].path, ["A", "D"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
