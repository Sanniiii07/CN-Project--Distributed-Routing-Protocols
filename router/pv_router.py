"""
Path Vector Router with UDP Network Integration.
Runs an independent router process communicating over real UDP sockets,
exchanging Path Vector update messages (PV_UPDATE) with BGP-style loop detection.
Part of Distributed Routing Protocols Project.
"""

import json
import os
import socket
import sys
import threading
import time
from typing import Dict, Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from algorithms.path_vector import PathVectorRouter

HOST: str = "127.0.0.1"
DEFAULT_PORT_MAP: Dict[str, int] = {
    "A": 5001,
    "B": 5002,
    "C": 5003,
    "D": 5004,
    "R1": 5001,
    "R2": 5002,
    "R3": 5003,
    "R4": 5004,
}
BUFFER_SIZE: int = 65535
UPDATE_INTERVAL: float = 5.0


class PVRouterProcess:
    """
    Independent router process running Path Vector over UDP.
    Exchanges PV_UPDATE JSON datagrams with neighbor processes.
    """

    def __init__(
        self,
        router_id: str,
        port: int,
        neighbours: Dict[str, float],
        port_map: Optional[Dict[str, int]] = None
    ):
        self.router_id = router_id
        self.port = port
        self.port_map = port_map or DEFAULT_PORT_MAP
        self.node = PathVectorRouter(router_id=router_id, neighbours=neighbours)

        self.running = False
        self.lock = threading.RLock()
        self.sock: Optional[socket.socket] = None

    def start(self):
        """Starts socket listener and periodic background advertisement loops."""
        self.running = True
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Disable connection reset notifications on Windows UDP
        if hasattr(socket, "SIO_UDP_CONNRESET"):
            try:
                self.sock.ioctl(socket.SIO_UDP_CONNRESET, False)
            except (OSError, AttributeError):
                pass

        self.sock.bind((HOST, self.port))
        self.sock.settimeout(1.0)

        print(f"[*] Path Vector Router '{self.router_id}' listening on UDP {HOST}:{self.port}")
        print(f"[*] Neighbors: {self.node.neighbours}")

        # Start background threads
        threading.Thread(target=self._receive_loop, daemon=True).start()
        threading.Thread(target=self._periodic_advertisement_loop, daemon=True).start()

        # Small delay to ensure all threads in peer processes are listening
        threading.Thread(target=self._delayed_initial_send, daemon=True).start()

    def _delayed_initial_send(self):
        time.sleep(0.1)
        self.send_advertisement_to_all()

    def send_advertisement_to_all(self):
        """Broadcasts current Path Vector routes to all connected neighbors."""
        with self.lock:
            if not self.running or not self.sock:
                return

            advertisement = self.node.create_advertisement()
            payload = json.dumps(advertisement).encode("utf-8")

            for nbr_id in list(self.node.neighbours.keys()):
                nbr_port = self.port_map.get(nbr_id)
                if nbr_port:
                    try:
                        self.sock.sendto(payload, (HOST, nbr_port))
                    except OSError as e:
                        print(f"[{self.router_id}] Send error to {nbr_id}: {e}")

    def _receive_loop(self):
        """Continuously receives and parses UDP packets from neighbors."""
        while self.running and self.sock:
            try:
                data, addr = self.sock.recvfrom(BUFFER_SIZE)
                message = json.loads(data.decode("utf-8"))

                if message.get("type") == "PV_UPDATE":
                    sender = message.get("sender")
                    routes = message.get("routes", {})

                    with self.lock:
                        changed = self.node.process_advertisement(sender, routes)
                        if changed:
                            print(f"\n[{self.router_id}] Routing table updated from {sender}'s advertisement:")
                            self.node.print_routing_table()
                            # Trigger immediate update to neighbors on change
                            self.send_advertisement_to_all()

            except socket.timeout:
                continue
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            except OSError:
                break

    def _periodic_advertisement_loop(self):
        """Periodically announces routes to ensure convergence."""
        while self.running:
            time.sleep(UPDATE_INTERVAL)
            if self.running:
                self.send_advertisement_to_all()

    def trigger_link_failure(self, neighbor_id: str):
        """Simulates physical link failure to a neighbor."""
        with self.lock:
            print(f"\n[!] Simulating link failure: {self.router_id} <-> {neighbor_id} DOWN")
            self.node.remove_neighbour(neighbor_id)
            self.node.print_routing_table()
            self.send_advertisement_to_all()
            self.send_advertisement_to_all()

    def stop(self):
        """Shuts down the router socket cleanly."""
        self.running = False
        if self.sock:
            self.sock.close()
        print(f"[*] Router {self.router_id} stopped.")


def load_neighbours_from_topology(router_id: str, topology_path: str) -> Dict[str, float]:
    """Parses standard topology file to find direct links for this router."""
    neighbours = {}
    if not os.path.exists(topology_path):
        return neighbours

    with open(topology_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split()
            # Support both "A B 2" and "LINK R1 R2 2"
            if len(parts) == 3:
                u, v, cost_str = parts
            elif len(parts) == 4 and parts[0] == "LINK":
                _, u, v, cost_str = parts
            else:
                continue

            try:
                cost = float(cost_str)
                if u == router_id:
                    neighbours[v] = cost
                elif v == router_id:
                    neighbours[u] = cost
            except ValueError:
                continue

    return neighbours


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python router/pv_router.py <RouterID> [topology_file]")
        print("Example: python router/pv_router.py A topology.txt")
        sys.exit(1)

    r_id = sys.argv[1].upper()
    top_file = sys.argv[2] if len(sys.argv) > 2 else os.path.join(PROJECT_ROOT, "topology.txt")

    if r_id not in DEFAULT_PORT_MAP:
        print(f"Error: Unknown router ID '{r_id}'. Valid IDs: {list(DEFAULT_PORT_MAP.keys())}")
        sys.exit(1)

    nbrs = load_neighbours_from_topology(r_id, top_file)
    r_port = DEFAULT_PORT_MAP[r_id]

    router_process = PVRouterProcess(router_id=r_id, port=r_port, neighbours=nbrs)
    router_process.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        router_process.stop()
