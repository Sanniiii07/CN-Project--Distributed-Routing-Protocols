"""
Convergence Tracker, Anomaly Detector, and Table Visualizer.
Part of Distributed Routing Protocols Project.
"""

from typing import Dict, List, Any, Optional, Tuple


class ConvergenceTracker:
    """
    Monitors distributed routing rounds, logs changes,
    detects forwarding anomalies (loops, black holes), and prints ASCII timelines.
    """

    def __init__(self):
        self.snapshots: List[Dict[str, Any]] = []

    def record_round(self, round_number: int, routers: Dict[str, Any], message_count: int = 0) -> None:
        """Capture a snapshot of the network state at this round."""
        table_snapshot = {}
        for r_id, router in routers.items():
            table_snapshot[r_id] = {}
            for dest, entry in router.routing_table.items():
                table_snapshot[r_id][dest] = {
                    "next_hop": entry.next_hop,
                    "cost": entry.cost,
                    "path": getattr(entry, "path", [r_id, entry.next_hop, dest])
                }

        self.snapshots.append({
            "round": round_number,
            "tables": table_snapshot,
            "message_count": message_count
        })

    def detect_forwarding_loop(self, router_tables: Dict[str, Any], source: str, destination: str) -> Tuple[bool, List[str]]:
        """
        Traces actual forwarding hop-by-hop from source to destination.
        Returns (has_loop, visited_hops).
        """
        visited = []
        curr = source

        while curr != destination:
            if curr in visited:
                # Cycle found!
                visited.append(curr)
                return True, visited

            visited.append(curr)

            # Check if current router has a route to destination
            table = router_tables.get(curr, {})
            route = table.get(destination)
            if not route:
                # Black hole: dropped packet
                return False, visited

            next_hop = route["next_hop"] if isinstance(route, dict) else getattr(route, "next_hop", None)
            if not next_hop or next_hop == curr:
                return False, visited

            curr = next_hop

        visited.append(destination)
        return False, visited

    def detect_all_loops(self, routers: Dict[str, Any]) -> List[Tuple[str, str, List[str]]]:
        """Scans all pairs (source, destination) for routing loops."""
        tables = {r_id: r.routing_table for r_id, r in routers.items()}
        loops = []
        nodes = list(routers.keys())

        for src in nodes:
            for dst in nodes:
                if src == dst:
                    continue
                has_loop, trace = self.detect_forwarding_loop(tables, src, dst)
                if has_loop:
                    loops.append((src, dst, trace))
        return loops

    def render_convergence_summary(self) -> None:
        """Prints a human-readable summary of convergence progression."""
        print("\n" + "=" * 60)
        print("           CONVERGENCE SUMMARY TIMELINE")
        print("=" * 60)

        total_rounds = len(self.snapshots)
        print(f"Total Simulation Rounds Recorded: {total_rounds}")

        for snap in self.snapshots:
            rnd = snap["round"]
            msgs = snap["message_count"]
            print(f"\n[Round {rnd}] - Messages Transmitted: {msgs}")
            print(f"{'Router':<8}{'Dest':<8}{'Next Hop':<12}{'Cost':<8}{'Path'}")
            print("-" * 50)
            for r_id, tbl in sorted(snap["tables"].items()):
                for dst, rinfo in sorted(tbl.items()):
                    path_str = " -> ".join(rinfo.get("path", []))
                    cost_val = rinfo.get("cost", 0)
                    cost_str = f"{int(cost_val)}" if isinstance(cost_val, (int, float)) and cost_val.is_integer() else f"{cost_val}"
                    print(f"{r_id:<8}{dst:<8}{rinfo['next_hop']:<12}{cost_str:<8}{path_str}")

        print("=" * 60 + "\n")
