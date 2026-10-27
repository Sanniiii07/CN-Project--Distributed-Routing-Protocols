import os
import sys
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "algorithms"))

from dijkstra import read_topology, dijkstra, get_path


TOPOLOGY_FILE = os.path.join(
    PROJECT_ROOT, "config", "topology.txt"
)


class TestDijkstra(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.graph = read_topology(TOPOLOGY_FILE)

    def test_distances_from_A(self):
        distances, _ = dijkstra(self.graph, "A")

        expected = {
            "A": 0,
            "B": 2,
            "C": 5,
            "D": 5
        }

        self.assertEqual(distances, expected)

    def test_shortest_paths_from_A(self):
        distances, previous = dijkstra(self.graph, "A")

        self.assertEqual(get_path(previous, "A", "A"), ["A"])
        self.assertEqual(get_path(previous, "A", "B"), ["A", "B"])
        self.assertEqual(get_path(previous, "A", "C"), ["A", "B", "C"])
        self.assertEqual(get_path(previous, "A", "D"), ["A", "D"])

    def test_distances_from_all_routers(self):
        expected = {
            "A": {"A": 0, "B": 2, "C": 5, "D": 5},
            "B": {"A": 2, "B": 0, "C": 3, "D": 4},
            "C": {"A": 5, "B": 3, "C": 0, "D": 1},
            "D": {"A": 5, "B": 4, "C": 1, "D": 0}
        }

        for source, expected_distances in expected.items():
            distances, _ = dijkstra(self.graph, source)
            self.assertEqual(distances, expected_distances)

    def test_invalid_source(self):
        with self.assertRaises(ValueError):
            dijkstra(self.graph, "Z")


if __name__ == "__main__":
    unittest.main(verbosity=2)