import socket
import json
import sys
import time
import threading
import heapq
import os

HOST = "127.0.0.1"
PORT_MAP = {"A": 5001, "B": 5002, "C": 5003, "D": 5004}
LSA_INTERVAL = 15
LSA_TIMEOUT = 40
BUFFER_SIZE = 65535
def dijkstra(graph, source):
    distances = {n: float("inf") for n in graph}
    previous = {n: None for n in graph}
    distances[source] = 0
    queue = [(0, source)]
    while queue:
        distance, node = heapq.heappop(queue)
        if distance != distances[node]:
            continue

        for neighbour, cost in graph[node].items():
            new_distance = distance + cost

            if new_distance < distances[neighbour]:
                distances[neighbour] = new_distance
                previous[neighbour] = node
                heapq.heappush(queue, (new_distance, neighbour))

    return distances, previous
def get_path(previous, source, destination):
    path = []
    node = destination

    while node is not None:
        path.append(node)

        if node == source:
            return path[::-1]

        node = previous.get(node)

    return []
class Router:
    def __init__(self, router_id, port, topology_file):
        self.router_id = router_id
        self.port = port
        self.running = True
        self.lock = threading.RLock()
        self.neighbours = {}
        self.lsdb = {}
        self.routing_table = {}
        self.sequence_number = 0
        self.lsa_received_time = {}

        with open(topology_file, encoding="utf-8") as file:
            for line in file:
                parts = line.split()

                if not parts or parts[0].startswith("#"):
                    continue

                if len(parts) != 3:
                    raise ValueError(f"Invalid topology: {line.strip()}")

                a, b, cost_text = parts
                cost = int(cost_text)

                if a not in PORT_MAP or b not in PORT_MAP or a == b or cost <= 0:
                    raise ValueError(f"Invalid link: {line.strip()}")

                if a == router_id:
                    self.neighbours[b] = cost

                if b == router_id:
                    self.neighbours[a] = cost

        if not self.neighbours:
            raise ValueError(f"No neighbours for {router_id}")

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        if hasattr(socket, "SIO_UDP_CONNRESET"):
            try:
                self.sock.ioctl(socket.SIO_UDP_CONNRESET, False)
            except (OSError, AttributeError):
                pass

        self.sock.bind((HOST, port))
        self.sock.settimeout(1)
    def send_message(self, neighbour, message):
        try:
            self.sock.sendto(
                json.dumps(message).encode("utf-8"),
                (HOST, PORT_MAP[neighbour])
            )
        except OSError as error:
            if self.running:
                print(f"Router {self.router_id}: send error: {error}")
    def create_lsa(self):
        self.sequence_number += 1

        return {
            "type": "LSA",
            "origin": self.router_id,
            "seq": self.sequence_number,
            "age": 0,
            "neighbors": dict(self.neighbours)
        }
    def flood_lsa(self, lsa, previous_sender=None):
        for neighbour in self.neighbours:
            if neighbour == previous_sender or neighbour == lsa["origin"]:
                continue

            message = dict(lsa)
            message["sender"] = self.router_id
            self.send_message(neighbour, message)
    def originate_lsa(self):
        with self.lock:
            if not self.running:
                return

            lsa = self.create_lsa()
            self.lsdb[self.router_id] = lsa
            self.lsa_received_time[self.router_id] = time.monotonic()
            self.compute_routes()
            self.flood_lsa(lsa)
    def install_lsa(self, lsa):
        origin = lsa.get("origin")
        seq = lsa.get("seq")
        neighbours = lsa.get("neighbors")

        if origin not in PORT_MAP or origin == self.router_id:
            return False

        if not isinstance(seq, int) or seq < 1:
            return False

        if not isinstance(neighbours, dict):
            return False

        for neighbour, cost in neighbours.items():
            if (
                neighbour not in PORT_MAP
                or neighbour == origin
                or not isinstance(cost, int)
                or cost <= 0
            ):
                return False

        old_lsa = self.lsdb.get(origin)

        if old_lsa and seq <= old_lsa["seq"]:
            return False

        self.lsdb[origin] = {
            "type": "LSA",
            "origin": origin,
            "seq": seq,
            "age": 0,
            "neighbors": dict(neighbours)
        }

        self.lsa_received_time[origin] = time.monotonic()
        return True
    def build_graph(self):
        graph = {router: {} for router in PORT_MAP}

        for origin, lsa in self.lsdb.items():
            for neighbour, cost in lsa["neighbors"].items():
                graph[origin][neighbour] = cost
                graph[neighbour][origin] = cost

        return graph
    def compute_routes(self):
        graph = self.build_graph()
        distances, previous = dijkstra(graph, self.router_id)
        table = {}

        for destination, cost in distances.items():
            if destination == self.router_id or cost == float("inf"):
                continue

            path = get_path(previous, self.router_id, destination)

            if len(path) > 1:
                table[destination] = {
                    "next_hop": path[1],
                    "cost": cost,
                    "path": path
                }
        if table != self.routing_table:
            self.routing_table = table
            self.print_routing_table()
    def print_routing_table(self):
        print(f"\nRouter {self.router_id} Routing Table")
        print(f"{'Destination':<15}{'Next Hop':<12}{'Cost':<8}Path")

        for destination, route in sorted(self.routing_table.items()):
            path = " -> ".join(route["path"])
            print(
                f"{destination:<15}{route['next_hop']:<12}"
                f"{route['cost']:<8}{path}"
            )

        print("-" * 50)

    def process_message(self, message, address):
        if not isinstance(message, dict) or message.get("type") != "LSA":
            return

        sender = message.get("sender")

        if sender not in self.neighbours:
            return

        if address[0] != HOST or address[1] != PORT_MAP[sender]:
            return

        age = message.get("age", 0)

        if not isinstance(age, (int, float)) or age < 0 or age > LSA_TIMEOUT:
            return

        with self.lock:
            if not self.running:
                return

            if self.install_lsa(message):
                origin = message["origin"]
                self.flood_lsa(self.lsdb[origin], sender)
                self.compute_routes()

    def receive_loop(self):
        while self.running:
            try:
                data, address = self.sock.recvfrom(BUFFER_SIZE)

                try:
                    message = json.loads(data.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    continue

                self.process_message(message, address)

            except socket.timeout:
                continue

            except ConnectionResetError:
                continue

            except OSError as error:
                if self.running:
                    print(f"Router {self.router_id}: socket error: {error}")
                break

    def periodic_lsa_loop(self):
        while self.running:
            time.sleep(LSA_INTERVAL)

            if self.running:
                self.originate_lsa()

    def expiry_loop(self):
        while self.running:
            time.sleep(1)

            with self.lock:
                now = time.monotonic()
                changed = False

                for origin in list(self.lsdb):
                    if origin == self.router_id:
                        continue

                    last_seen = self.lsa_received_time.get(origin, 0)

                    if now - last_seen > LSA_TIMEOUT:
                        del self.lsdb[origin]
                        self.lsa_received_time.pop(origin, None)
                        changed = True

                if changed:
                    self.compute_routes()

    def start(self):
        print(f"Router {self.router_id} started at {HOST}:{self.port}")
        print("Neighbours:", self.neighbours)

        threading.Thread(target=self.receive_loop, daemon=True).start()
        threading.Thread(target=self.periodic_lsa_loop, daemon=True).start()
        threading.Thread(target=self.expiry_loop, daemon=True).start()

        try:
            self.originate_lsa()

            while self.running:
                time.sleep(0.5)

        except KeyboardInterrupt:
            print(f"\nRouter {self.router_id} shutting down")

        finally:
            self.running = False
            self.sock.close()

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1].upper() not in PORT_MAP:
        print("Usage: python -m router.router A")
        sys.exit(1)

    router_id = sys.argv[1].upper()
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    topology = os.path.join(root, "config", "topology.txt")
    try:
        Router(router_id, PORT_MAP[router_id], topology).start()
    except (OSError, ValueError) as error:
        print(f"Router startup failed: {error}")