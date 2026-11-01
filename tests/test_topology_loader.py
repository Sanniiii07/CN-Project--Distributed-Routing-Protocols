"""
Unit tests for the Shared Python Topology Loader module (config/topology_loader.py).
Verifies parsing of topology.conf, router port mappings, neighbor discovery,
and legacy format compatibility.
"""

import os
import sys
import tempfile
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config.topology_loader import (
    load_topology,
    get_port_map,
    get_router_neighbors,
    get_topology_graph,
    Topology,
    RouterInfo,
    LinkInfo,
)


class TestTopologyLoader(unittest.TestCase):
    """Test suite for topology loader."""

    def test_load_default_topology(self):
        """Verify that default config/topology.conf loads 4 routers and 6 links."""
        topo = load_topology()
        self.assertEqual(len(topo.routers), 4)
        self.assertEqual(len(topo.links), 6)
        self.assertEqual(topo.get_all_router_ids(), ["R1", "R2", "R3", "R4"])

    def test_router_details(self):
        """Verify router IPs and ports from topology.conf."""
        topo = load_topology()
        r1 = topo.get_router("R1")
        self.assertIsNotNone(r1)
        self.assertEqual(r1.router_id, "R1")
        self.assertEqual(r1.ip, "127.0.0.1")
        self.assertEqual(r1.port, 5001)

        r4 = topo.get_router("R4")
        self.assertIsNotNone(r4)
        self.assertEqual(r4.port, 5004)

    def test_neighbors_of_routers(self):
        """Verify neighbor calculations and link weights."""
        topo = load_topology()
        r1_nbrs = topo.get_neighbors("R1")
        self.assertEqual(r1_nbrs, {"R2": 2.0, "R3": 5.0, "R4": 8.0})

        r3_nbrs = topo.get_neighbors("R3")
        self.assertEqual(r3_nbrs, {"R1": 5.0, "R2": 4.0, "R4": 1.0})

    def test_port_map_with_aliases(self):
        """Verify port map contains both standard and legacy alias keys."""
        port_map = get_port_map()
        self.assertEqual(port_map["R1"], 5001)
        self.assertEqual(port_map["R2"], 5002)
        self.assertEqual(port_map["R3"], 5003)
        self.assertEqual(port_map["R4"], 5004)

        # Aliases
        self.assertEqual(port_map["A"], 5001)
        self.assertEqual(port_map["B"], 5002)
        self.assertEqual(port_map["C"], 5003)
        self.assertEqual(port_map["D"], 5004)

    def test_adjacency_list_format(self):
        """Verify graph adjacency list structure for Dijkstra/Bellman-Ford."""
        graph = get_topology_graph()
        self.assertIn("R1", graph)
        self.assertEqual(graph["R1"]["R2"], 2.0)
        self.assertEqual(graph["R2"]["R1"], 2.0)

    def test_custom_conf_parsing(self):
        """Verify parsing a temporary custom topology file."""
        custom_content = (
            "# Custom topology\n"
            "ROUTER X 127.0.0.1 7001\n"
            "ROUTER Y 127.0.0.1 7002\n"
            "LINK X Y 10.5\n"
        )
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".conf") as tmp:
            tmp.write(custom_content)
            tmp_path = tmp.name

        try:
            topo = load_topology(tmp_path)
            self.assertEqual(len(topo.routers), 2)
            self.assertEqual(len(topo.links), 1)
            self.assertEqual(topo.get_neighbors("X"), {"Y": 10.5})
            self.assertEqual(topo.get_port_map()["X"], 7001)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_invalid_syntax_handling(self):
        """Verify that malformed configuration directives raise ValueError."""
        invalid_content = "ROUTER BadRouter\n"
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".conf") as tmp:
            tmp.write(invalid_content)
            tmp_path = tmp.name

        try:
            with self.assertRaises(ValueError):
                load_topology(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_missing_file_raises_error(self):
        """Verify FileNotFoundError on non-existent path."""
        with self.assertRaises(FileNotFoundError):
            load_topology("non_existent_file_xyz_123.conf")


if __name__ == "__main__":
    unittest.main(verbosity=2)
