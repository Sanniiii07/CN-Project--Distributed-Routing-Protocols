"""
Comparative Convergence and Message Overhead Experiments.
Evaluates Path Vector vs Link State convergence rounds and message volume.
Part of Distributed Routing Protocols Project.
"""

import sys
import os
from typing import Dict, Tuple

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from algorithms.path_vector import PathVectorRouter
from events.event_engine import EventEngine, NetworkEvent
from visualization.convergence import ConvergenceTracker


class ExperimentBenchmark:
    """Runs automated convergence benchmarks comparing protocol performance."""

    def __init__(self):
        self.tracker = ConvergenceTracker()
        self.event_engine = EventEngine()

    def build_topology(self) -> Dict[str, PathVectorRouter]:
        """
        Builds standard 4-node diamond network:
          A --(2)-- B --(3)-- C --(1)-- D
          |                             |
          +------------(5)--------------+
        """
        return {
            "A": PathVectorRouter("A", {"B": 2.0, "D": 5.0}),
            "B": PathVectorRouter("B", {"A": 2.0, "C": 3.0}),
            "C": PathVectorRouter("C", {"B": 3.0, "D": 1.0}),
            "D": PathVectorRouter("D", {"A": 5.0, "C": 1.0}),
        }

    def simulate_path_vector_convergence(self, routers: Dict[str, PathVectorRouter], max_rounds: int = 15) -> Tuple[int, int]:
        """
        Simulates iterative message passing until all routing tables stabilize.
        Returns: (rounds_to_converge, total_messages_sent)
        """
        rounds = 0
        total_messages = 0
        converged = False

        while not converged and rounds < max_rounds:
            rounds += 1
            converged = True

            # Step 1: Every router generates an advertisement
            advertisements = {}
            for r_id, router in routers.items():
                advertisements[r_id] = router.create_advertisement()

            # Step 2: Distribute to connected neighbors
            for r_id, ad in advertisements.items():
                for nbr_id in list(routers[r_id].neighbours.keys()):
                    total_messages += 1
                    changed = routers[nbr_id].process_advertisement(r_id, ad["routes"])
                    if changed:
                        converged = False

            self.tracker.record_round(rounds, routers, message_count=total_messages)

        return rounds, total_messages

    def run_all(self):
        print("=" * 65)
        print("   DISTRIBUTED ROUTING EXPERIMENT BENCHMARK")
        print("=" * 65)

        # Experiment 1: Cold Start Convergence
        print("\n[Experiment 1] Initial Cold Start Convergence")
        routers = self.build_topology()
        rounds, msgs = self.simulate_path_vector_convergence(routers)
        print(f" -> Result: Converged in {rounds} rounds using {msgs} messages.")

        # Experiment 2: Dynamic Link Failure (Link A-D fails)
        print("\n[Experiment 2] Link Failure Perturbation (Link A <-> D DOWN)")
        event_down = NetworkEvent(event_type="LINK_DOWN", time_offset=1.0, node_a="A", node_b="D")
        self.event_engine.apply_event(event_down, routers)
        fail_rounds, fail_msgs = self.simulate_path_vector_convergence(routers)
        print(f" -> Result: Network adapted in {fail_rounds} rounds using {fail_msgs} messages.")
        print(f" -> Route A to D now uses alternative path: {' -> '.join(routers['A'].routing_table['D'].path)}")

        # Experiment 3: Link Recovery (Link A-D recovers with cost 5)
        print("\n[Experiment 3] Link Recovery Perturbation (Link A <-> D UP with cost 5.0)")
        event_up = NetworkEvent(event_type="LINK_UP", time_offset=2.0, node_a="A", node_b="D", new_cost=5.0)
        self.event_engine.apply_event(event_up, routers)
        rec_rounds, rec_msgs = self.simulate_path_vector_convergence(routers)
        print(f" -> Result: Re-converged in {rec_rounds} rounds using {rec_msgs} messages.")

        print("\n" + "=" * 65)
        print("                     BENCHMARK SUMMARY")
        print("=" * 65)
        print(f"{'Scenario':<30}{'Rounds':<12}{'Messages Sent'}")
        print("-" * 65)
        print(f"{'1. Cold Start':<30}{rounds:<12}{msgs}")
        print(f"{'2. Link Failure (A-D)':<30}{fail_rounds:<12}{fail_msgs}")
        print(f"{'3. Link Recovery (A-D)':<30}{rec_rounds:<12}{rec_msgs}")
        print("=" * 65 + "\n")


if __name__ == "__main__":
    benchmark = ExperimentBenchmark()
    benchmark.run_all()
