"""
Automated Integration Test for Path Vector UDP Router Processes.
Spawns 4 independent UDP router processes on localhost and tests real convergence.
"""

import unittest
import time
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from router.pv_router import PVRouterProcess


class TestPVRouterUDPIntegration(unittest.TestCase):

    def test_four_routers_udp_convergence(self):
        """
        Spawns 4 UDP router processes (A, B, C, D) using non-standard ports
        to avoid collisions, verifies message exchange over UDP and convergence.
        """
        test_ports = {
            "A": 16001,
            "B": 16002,
            "C": 16003,
            "D": 16004,
        }

        # Diamond topology
        routers = {
            "A": PVRouterProcess("A", test_ports["A"], {"B": 2.0, "D": 5.0}, test_ports),
            "B": PVRouterProcess("B", test_ports["B"], {"A": 2.0, "C": 3.0}, test_ports),
            "C": PVRouterProcess("C", test_ports["C"], {"B": 3.0, "D": 1.0}, test_ports),
            "D": PVRouterProcess("D", test_ports["D"], {"A": 5.0, "C": 1.0}, test_ports),
        }

        # Start all 4 router processes
        for r in routers.values():
            r.start()

        # Allow 2 seconds for UDP datagram exchange and convergence
        time.sleep(2.0)

        try:
            # Check Router A's learned path to C: Should be [A, B, C]
            route_to_c = routers["A"].node.routing_table.get("C")
            self.assertIsNotNone(route_to_c)
            self.assertEqual(route_to_c.path, ["A", "B", "C"])
            self.assertEqual(route_to_c.cost, 5.0)

            # Check Router A's path to D: Direct link is cost 5
            route_to_d = routers["A"].node.routing_table.get("D")
            self.assertIsNotNone(route_to_d)
            self.assertEqual(route_to_d.path, ["A", "D"])
            self.assertEqual(route_to_d.cost, 5.0)

            # Test dynamic link failure over UDP
            routers["A"].trigger_link_failure("D")
            routers["D"].trigger_link_failure("A")
            routers["B"].send_advertisement_to_all()
            time.sleep(1.5)

            # After link failure, route A -> D must adapt to backup path A -> B -> C -> D
            route_to_d_backup = routers["A"].node.routing_table.get("D")
            self.assertIsNotNone(route_to_d_backup)
            self.assertEqual(route_to_d_backup.path, ["A", "B", "C", "D"])
            self.assertEqual(route_to_d_backup.cost, 6.0)

        finally:
            for r in routers.values():
                r.stop()


if __name__ == "__main__":
    unittest.main(verbosity=2)
