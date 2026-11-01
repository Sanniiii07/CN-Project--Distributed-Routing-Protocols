"""
Topology Loader Module for Distributed Routing Protocols.
Parses topology configuration files (config/topology.conf) into structured
Router and Link objects, providing dynamic port maps and neighbor link costs.
Replaces hardcoded dictionaries across the project.
"""

import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# Locate project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

DEFAULT_CONFIG_FILE = os.path.join(PROJECT_ROOT, "config", "topology.conf")


@dataclass
class RouterInfo:
    """Represents a router node definition."""
    router_id: str
    ip: str = "127.0.0.1"
    port: int = 5000

    def __str__(self) -> str:
        return f"Router({self.router_id} @ {self.ip}:{self.port})"


@dataclass
class LinkInfo:
    """Represents a bidirectional link between two routers with an associated cost."""
    router1: str
    router2: str
    cost: float

    def connects(self, router_id: str) -> bool:
        """Returns True if this link attaches to router_id."""
        return self.router1 == router_id or self.router2 == router_id

    def other_end(self, router_id: str) -> Optional[str]:
        """Returns the other router connected by this link, or None if router_id is not attached."""
        if self.router1 == router_id:
            return self.router2
        if self.router2 == router_id:
            return self.router1
        return None

    def __str__(self) -> str:
        return f"Link({self.router1} <-> {self.router2}, cost={self.cost})"


class Topology:
    """
    Stores and queries loaded routers and links.
    Provides convenience methods for routing algorithms and socket processes.
    """

    def __init__(self):
        self.routers: Dict[str, RouterInfo] = {}
        self.links: List[LinkInfo] = []

    def add_router(self, router_id: str, ip: str = "127.0.0.1", port: int = 5000) -> RouterInfo:
        """Adds or updates a router definition."""
        router = RouterInfo(router_id=str(router_id), ip=str(ip), port=int(port))
        self.routers[str(router_id)] = router
        return router

    def add_link(self, router1: str, router2: str, cost: float) -> LinkInfo:
        """Adds a bidirectional link between two routers."""
        link = LinkInfo(router1=str(router1), router2=str(router2), cost=float(cost))
        self.links.append(link)
        return link

    def get_router(self, router_id: str) -> Optional[RouterInfo]:
        """Returns RouterInfo for given ID, or None if not found."""
        return self.routers.get(str(router_id))

    def get_all_router_ids(self) -> List[str]:
        """Returns sorted list of all configured router IDs."""
        return sorted(self.routers.keys())

    def get_port_map(self, include_aliases: bool = True) -> Dict[str, int]:
        """
        Returns a dictionary mapping router IDs to their configured UDP ports.
        If include_aliases=True, maps both 'R1' <-> 'A', 'R2' <-> 'B', etc.,
        ensuring full backward compatibility across all legacy test scripts.
        """
        port_map: Dict[str, int] = {}
        for r_id, r_info in self.routers.items():
            port_map[r_id] = r_info.port

        if include_aliases:
            # Map R1..R4 <-> A..D
            alias_forward = {"R1": "A", "R2": "B", "R3": "C", "R4": "D"}
            alias_reverse = {v: k for k, v in alias_forward.items()}

            for r_id, port in list(port_map.items()):
                if r_id in alias_forward:
                    port_map.setdefault(alias_forward[r_id], port)
                elif r_id in alias_reverse:
                    port_map.setdefault(alias_reverse[r_id], port)

        return port_map

    def get_neighbors(self, router_id: str) -> Dict[str, float]:
        """
        Returns a dictionary mapping neighboring router IDs to link cost
        for the specified router.
        """
        router_id = str(router_id)
        neighbors: Dict[str, float] = {}
        for link in self.links:
            other = link.other_end(router_id)
            if other is not None:
                neighbors[other] = link.cost
        return neighbors

    def get_adjacency_list(self) -> Dict[str, Dict[str, float]]:
        """
        Returns a full adjacency list {router: {neighbor: cost}}
        suitable for graph algorithms such as Dijkstra.
        """
        graph: Dict[str, Dict[str, float]] = {r_id: {} for r_id in self.routers}
        for link in self.links:
            graph.setdefault(link.router1, {})[link.router2] = link.cost
            graph.setdefault(link.router2, {})[link.router1] = link.cost
        return graph

    def display(self) -> None:
        """Prints a human-readable summary of the loaded topology."""
        print("=== Topology Configuration ===")
        print(f"Total Routers: {len(self.routers)} | Total Links: {len(self.links)}\n")
        print("Routers:")
        for r_id in self.get_all_router_ids():
            r = self.routers[r_id]
            nbrs = self.get_neighbors(r_id)
            nbr_str = ", ".join(f"{nbr}(cost={c})" for nbr, c in nbrs.items()) or "None"
            print(f"  [{r.router_id}] IP: {r.ip:<12} Port: {r.port:<6} Neighbors: {nbr_str}")
        print("\nLinks:")
        for link in self.links:
            print(f"  {link.router1} <---> {link.router2}  (Cost: {link.cost})")
        print("==============================\n")


def find_topology_file(filepath: Optional[str] = None) -> str:
    """Resolves the topology file path across standard search locations."""
    if filepath is not None:
        if os.path.isfile(filepath):
            return os.path.abspath(filepath)
        raise FileNotFoundError(f"Topology file not found: {filepath}")

    candidates = [
        os.path.join(PROJECT_ROOT, "config", "topology.conf"),
        os.path.join(PROJECT_ROOT, "topology.conf"),
        os.path.join("config", "topology.conf"),
        os.path.join("..", "config", "topology.conf"),
        DEFAULT_CONFIG_FILE,
        os.path.join(PROJECT_ROOT, "config", "topology.txt"),
        os.path.join(PROJECT_ROOT, "topology.txt"),
    ]

    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return os.path.abspath(candidate)

    raise FileNotFoundError(f"No default topology file found at: {DEFAULT_CONFIG_FILE}")


def load_topology(filepath: Optional[str] = None) -> Topology:
    """
    Parses a topology file (e.g. config/topology.conf) into a Topology instance.

    Supported syntax:
      ROUTER <id> <ip> <port>
      LINK <router1> <router2> <cost>
      # comments and blank lines are ignored

    Also supports simple 3-token legacy files (e.g. 'A B 2').
    """
    target_path = find_topology_file(filepath)
    topology = Topology()

    if not os.path.isfile(target_path):
        raise FileNotFoundError(f"Topology file not found: {target_path}")

    # Fallback port assignment base if implicit router lines are encountered
    next_auto_port = 5001

    with open(target_path, "r", encoding="utf-8") as f:
        for line_num, raw_line in enumerate(f, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split()

            if parts[0].upper() == "ROUTER":
                # Syntax: ROUTER <id> <ip> <port>
                if len(parts) < 4:
                    raise ValueError(f"Invalid ROUTER directive at line {line_num}: {line}")
                r_id = parts[1]
                ip = parts[2]
                try:
                    port = int(parts[3])
                except ValueError:
                    raise ValueError(f"Invalid port '{parts[3]}' at line {line_num}")
                topology.add_router(router_id=r_id, ip=ip, port=port)

            elif parts[0].upper() == "LINK":
                # Syntax: LINK <r1> <r2> <cost>
                if len(parts) < 4:
                    raise ValueError(f"Invalid LINK directive at line {line_num}: {line}")
                r1 = parts[1]
                r2 = parts[2]
                try:
                    cost = float(parts[3])
                except ValueError:
                    raise ValueError(f"Invalid link cost '{parts[3]}' at line {line_num}")

                # Ensure endpoints are registered
                if r1 not in topology.routers:
                    topology.add_router(router_id=r1, ip="127.0.0.1", port=next_auto_port)
                    next_auto_port += 1
                if r2 not in topology.routers:
                    topology.add_router(router_id=r2, ip="127.0.0.1", port=next_auto_port)
                    next_auto_port += 1

                topology.add_link(router1=r1, router2=r2, cost=cost)

            elif len(parts) == 3:
                # Legacy simple format: <r1> <r2> <cost>
                r1, r2, cost_str = parts
                try:
                    cost = float(cost_str)
                except ValueError:
                    raise ValueError(f"Invalid link cost '{cost_str}' at line {line_num}")

                if r1 not in topology.routers:
                    topology.add_router(router_id=r1, ip="127.0.0.1", port=next_auto_port)
                    next_auto_port += 1
                if r2 not in topology.routers:
                    topology.add_router(router_id=r2, ip="127.0.0.1", port=next_auto_port)
                    next_auto_port += 1

                topology.add_link(router1=r1, router2=r2, cost=cost)

    return topology


# Convenience helper functions
def get_port_map(filepath: Optional[str] = None) -> Dict[str, int]:
    """Convenience helper to retrieve port mapping dictionary."""
    return load_topology(filepath).get_port_map()


def get_router_neighbors(router_id: str, filepath: Optional[str] = None) -> Dict[str, float]:
    """Convenience helper to retrieve neighbors of a router."""
    return load_topology(filepath).get_neighbors(router_id)


def get_topology_graph(filepath: Optional[str] = None) -> Dict[str, Dict[str, float]]:
    """Convenience helper to retrieve adjacency list for Dijkstra."""
    return load_topology(filepath).get_adjacency_list()


if __name__ == "__main__":
    print("Testing config/topology_loader.py:")
    try:
        topo = load_topology()
        topo.display()
        print("Port map:", topo.get_port_map())
        print("Neighbors of R1:", topo.get_neighbors("R1"))
        print("\nTopology loader test passed successfully!")
    except Exception as exc:
        print(f"Error loading topology: {exc}")
        sys.exit(1)
