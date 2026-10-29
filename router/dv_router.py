"""
Distance Vector Router with UDP Network Integration.
Handles live UDP socket communication to exchange Distance Vector updates
(DV_UPDATE) between distributed router processes.
"""

import json
import os
import socket
import sys
import threading
import time
from typing import Dict, Optional

# Ensure project root is accessible for imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from algorithms.distance_vector import (
    DistanceVectorNode,
    LOOP_PREVENTION_NONE,
    LOOP_PREVENTION_SPLIT_HORIZON,
    LOOP_PREVENTION_POISONED_REVERSE,
)

HOST: str = "127.0.0.1"
DEFAULT_PORT_MAP: Dict[str, int] = {
    "R1": 5001,
    "R2": 5002,
    "R3": 5003,
    "R4": 5004,
    "A": 5001,
    "B": 5002,
    "C": 5003,
    "D": 5004,
}
BUFFER_SIZE: int = 65535


class DVRouter:
    """
    A standalone router process running the Distance Vector protocol
    over UDP sockets.
    """

    def __init__(
        self,
        router_id: str,
        port: int,
        neighbours: Dict[str, float],
        port_map: Optional[Dict[str, int]] = None,
        loop_prevention: str = LOOP_PREVENTION_POISONED_REVERSE,
        update_interval: float = 5.0,
    ):
        self.router_id = str(router_id)
        self.port = int(port)
        self.port_map = dict(port_map) if port_map else dict(DEFAULT_PORT_MAP)
        self.update_interval = update_interval
        self.running = False
        self.lock = threading.RLock()

        # Distance Vector routing engine
        self.node = DistanceVectorNode(
            router_id=self.router_id,
            neighbours=neighbours,
            loop_prevention=loop_prevention,
        )

        # Setup UDP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Windows UDP connection reset fix
        if hasattr(socket, "SIO_UDP_CONNRESET"):
            try:
                self.sock.ioctl(socket.SIO_UDP_CONNRESET, False)
            except (OSError, AttributeError):
                pass

        self.sock.bind((HOST, self.port))
        self.sock.settimeout(1.0)

    def send_update(self, neighbour_id: str) -> bool:
        """
        Sends a DV_UPDATE message to a specific neighbour over UDP.
        Applies Split Horizon or Poisoned Reverse for that neighbour.
        """
        neighbour_id = str(neighbour_id)
        target_port = self.port_map.get(neighbour_id)
        if not target_port:
            return False

        message = self.node.create_advertisement(for_neighbour=neighbour_id)
        data = json.dumps(message).encode("utf-8")

        try:
            self.sock.sendto(data, (HOST, target_port))
            return True
        except OSError as error:
            if self.running:
                print(f"[{self.router_id}] Send error to {neighbour_id}: {error}")
            return False

    def send_all_updates(self) -> None:
        """Sends neighbor-specific DV_UPDATE messages to all active neighbours."""
        with self.lock:
            for neighbour_id in list(self.node.neighbours.keys()):
                self.send_update(neighbour_id)

    def process_incoming_datagram(self, data: bytes, address: tuple) -> None:
        """Parses and processes an incoming UDP datagram."""
        try:
            message = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return

        if not isinstance(message, dict) or message.get("type") != "DV_UPDATE":
            return

        sender = message.get("sender")
        if not sender:
            return

        with self.lock:
            # Process incoming vector and check if our routing table changed
            changed = self.node.process_advertisement(message)
            if changed:
                print(f"[{self.router_id}] Routes updated via DV_UPDATE from {sender}:")
                self.node.routing_table.display()
                # Triggered update: immediately inform neighbours about the change
                self.send_all_updates()

    def receive_loop(self) -> None:
        """Background thread listening for incoming UDP messages."""
        while self.running:
            try:
                data, address = self.sock.recvfrom(BUFFER_SIZE)
                self.process_incoming_datagram(data, address)
            except socket.timeout:
                continue
            except OSError:
                break

    def periodic_update_loop(self) -> None:
        """Background thread broadcasting periodic routing table advertisements."""
        while self.running:
            time.sleep(self.update_interval)
            if self.running:
                self.send_all_updates()

    def start(self) -> None:
        """Starts the router's background network threads."""
        self.running = True
        print(f"[{self.router_id}] DV Router started on UDP port {self.port}")
        print(f"[{self.router_id}] Initial neighbours: {self.node.neighbours}")

        self.recv_thread = threading.Thread(target=self.receive_loop, daemon=True)
        self.recv_thread.start()

        self.periodic_thread = threading.Thread(target=self.periodic_update_loop, daemon=True)
        self.periodic_thread.start()

        # Send initial distance vector announcement
        self.send_all_updates()

    def stop(self) -> None:
        """Gracefully stops threads and closes the UDP socket."""
        self.running = False
        try:
            self.sock.close()
        except OSError:
            pass


if __name__ == "__main__":
    print("=== UDP Router Messaging Integration Demo (Commit 07) ===")
    print("Starting two live router instances on localhost UDP sockets...")

    test_ports = {"R1": 5501, "R2": 5502}

    # Router R1 is on port 5501 with neighbour R2 (cost 2)
    router1 = DVRouter(
        router_id="R1",
        port=test_ports["R1"],
        neighbours={"R2": 2.0},
        port_map=test_ports,
        update_interval=10.0,
    )

    # Router R2 is on port 5502 with neighbours R1 (cost 2) and R3 (cost 3)
    router2 = DVRouter(
        router_id="R2",
        port=test_ports["R2"],
        neighbours={"R1": 2.0, "R3": 3.0},
        port_map=test_ports,
        update_interval=10.0,
    )

    try:
        router1.start()
        router2.start()

        print("\nExchanging initial DV updates over UDP...")
        # Give background UDP threads a moment to exchange packets
        time.sleep(1.5)

        print("\nFinal verified routing table for Router R1 (learned R3 via UDP):")
        router1.node.routing_table.display()

        cost_to_r3 = router1.node.routing_table.get_cost("R3")
        hop_to_r3 = router1.node.routing_table.get_next_hop("R3")
        print(f"R1 -> R3: Cost={cost_to_r3}, NextHop={hop_to_r3}")

        if cost_to_r3 == 5.0 and hop_to_r3 == "R2":
            print("\nVisible result: Separate router processes successfully exchanged route information over UDP!")
        else:
            print("\nRouting exchange in progress...")

    finally:
        router1.stop()
        router2.stop()
        print("\nUDP Router processes stopped cleanly.")
