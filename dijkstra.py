import heapq


def read_topology(filename):
    graph = {}

    with open(filename, "r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            parts = line.split()

            if len(parts) != 3:
                raise ValueError(
                    f"Invalid topology at line {line_number}: {line}"
                )

            a, b, cost_text = parts

            try:
                cost = float(cost_text)
            except ValueError:
                raise ValueError(
                    f"Invalid link cost at line {line_number}: {cost_text}"
                )

            if cost < 0:
                raise ValueError("Dijkstra requires non-negative link costs.")

            graph.setdefault(a, {})
            graph.setdefault(b, {})

            graph[a][b] = cost
            graph[b][a] = cost

    return graph


def dijkstra(graph, source):
    if source not in graph:
        raise ValueError(f"Source router '{source}' is not in the topology.")

    distances = {vertex: float("inf") for vertex in graph}
    previous = {vertex: None for vertex in graph}

    distances[source] = 0
    priority_queue = [(0, source)]

    while priority_queue:
        current_distance, current = heapq.heappop(priority_queue)

        if current_distance != distances[current]:
            continue

        for neighbour, cost in graph[current].items():
            new_distance = current_distance + cost

            if new_distance < distances[neighbour]:
                distances[neighbour] = new_distance
                previous[neighbour] = current

                heapq.heappush(
                    priority_queue,
                    (new_distance, neighbour)
                )

    return distances, previous
def get_path(previous, source, destination):
    if source == destination:
        return [source]
    if destination not in previous:
        return []
    path = []
    current = destination
    while current is not None:
        path.append(current)
        if current == source:
            path.reverse()
            return path
        current = previous[current]
    return []
if __name__ == "__main__":
    graph = read_topology("config/topology.txt")
    for source in sorted(graph):
        distances, previous = dijkstra(graph, source)
        print(f"\nRouting table for Router {source}")
        print(f"{'Destination':<15}{'Cost':<10}{'Path'}")
        for destination in sorted(graph):
            path = get_path(previous, source, destination)
            cost = distances[destination]

            cost_text = (
                str(int(cost)) if cost != float("inf") and cost.is_integer()
                else str(cost)
            )
            path_text = " -> ".join(path) if path else "Unreachable"
            print(f"{destination:<15}{cost_text:<10}{path_text}")