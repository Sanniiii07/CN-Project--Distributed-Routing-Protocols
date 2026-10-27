import time
class LSA:
    MAX_AGE = 10
    def __init__(
        self,
        origin,
        neighbours,
        sequence_number=0,
        age=0
    ):
        self.origin = origin
        self.neighbours = dict(neighbours)
        self.sequence_number = sequence_number
        self.age = age
        self.created_at = time.monotonic()
    def is_expired(self):
        return self.age >= self.MAX_AGE
    def __repr__(self):
        return (
            f"LSA(origin={self.origin}, "
            f"neighbours={self.neighbours}, "
            f"sequence_number={self.sequence_number}, "
            f"age={self.age})"
        )
class LSADatabase:
    def __init__(self):
        self.database = {}
    def update(self, lsa):
        current = self.database.get(lsa.origin)
        if (
            current is None
            or lsa.sequence_number > current.sequence_number
        ):
            self.database[lsa.origin] = lsa
            return True
        return False
    def get(self, origin):
        return self.database.get(origin)
    def get_all(self):
        return dict(self.database)
    def age_lsas(self):
        expired = []
        for origin, lsa in self.database.items():
            lsa.age += 1
            if lsa.is_expired():
                expired.append(origin)
        for origin in expired:
            del self.database[origin]
        return expired
    def build_graph(self):
        graph = {}
        for origin, lsa in self.database.items():
            if lsa.is_expired():
                continue
            graph.setdefault(origin, {})
            for neighbour, cost in lsa.neighbours.items():
                graph.setdefault(neighbour, {})
                graph[origin][neighbour] = cost
        return graph
class LSAFlooder:
    def __init__(self, router_id, neighbours):
        self.router_id = router_id
        self.neighbours = dict(neighbours)
    def get_forwarding_neighbours(self, sender=None):
        return [
            neighbour
            for neighbour in self.neighbours
            if neighbour != sender
        ]
    def flood(self, lsa, sender=None):
        targets = self.get_forwarding_neighbours(sender)
        for neighbour in targets:
            print(
                f"[{self.router_id}] Forwarding LSA from "
                f"{lsa.origin} (seq={lsa.sequence_number}) "
                f"to {neighbour}"
            )
        return targets
if __name__ == "__main__":
    database = LSADatabase()
    lsa1 = LSA("A", {"B": 2, "D": 5}, sequence_number=1)
    lsa2 = LSA("A", {"B": 2, "D": 5}, sequence_number=2)
    print("Adding LSA 1:", database.update(lsa1))
    print("Adding LSA 2:", database.update(lsa2))
    print("Adding old LSA again:", database.update(lsa1))

    print("\nCurrent LS Database:")
    for origin, lsa in database.get_all().items():
        print(origin, "->", lsa)
    flooder = LSAFlooder("B", {"A": 2, "C": 3})
    print("\nFlooding test:")
    flooder.flood(lsa2, sender="A")