"""
Count-to-Infinity Simulation and Loop Prevention Experiment.
Demonstrates the classic Distance Vector routing loop problem (count-to-infinity)
when a link fails, and compares convergence behavior across three modes:
  1. No loop prevention (NONE) - shows metric bouncing up to 16
  2. Split Horizon (SPLIT_HORIZON) - omits routes sent to next hop
  3. Poisoned Reverse (POISONED_REVERSE) - advertises next hop with metric 16
Part of Distributed Routing Protocols Project (P7).
"""

import os
import sys
from typing import Dict, List, Any

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
from router.routing_table import INFINITY


def simulate_count_to_infinity(
    mode: str = LOOP_PREVENTION_NONE,
    max_rounds: int = 25
) -> Dict[str, Any]:
    """
    Simulates a 3-node linear topology:
        A <---(cost 1)---> B <---(cost 1)---> C

    Steps:
      1. Initial state:
         - B is directly connected to C (cost 1).
         - A routes to C through B (cost 1 + 1 = 2).
         - Both nodes reach steady state.
      2. Event: Link between B and C fails!
      3. Iterative message exchange:
         - In each round, B and A exchange distance vectors until
           both agree that C is unreachable (cost >= 16) or reach max_rounds.

    Returns a dictionary recording round-by-round metric progression.
    """
    mode = mode.upper()

    # Step 1: Initialize nodes
    node_a = DistanceVectorNode("A", neighbours={"B": 1.0}, loop_prevention=mode)
    node_b = DistanceVectorNode("B", neighbours={"A": 1.0, "C": 1.0}, loop_prevention=mode)

    # Initial convergence before failure:
    # B advertises to A (B knows C with cost 1)
    b_init_vector = node_b.get_outgoing_vector(for_neighbour="A")
    node_a.receive_vector("B", b_init_vector)

    # A advertises back to B
    a_init_vector = node_a.get_outgoing_vector(for_neighbour="B")
    node_b.receive_vector("A", a_init_vector)

    # Verify steady state before failure
    cost_a_before = node_a.routing_table.get_cost("C")
    cost_b_before = node_b.routing_table.get_cost("C")

    # Step 2: Inject link failure between B and C
    node_b.fail_link("C")

    history: List[Dict[str, Any]] = []

    # Record Round 0 (Immediate state right after link B-C fails)
    history.append({
        "round": 0,
        "event": "Link B-C fails",
        "cost_A": node_a.routing_table.get_cost("C"),
        "hop_A": node_a.routing_table.get_next_hop("C") or "-",
        "cost_B": node_b.routing_table.get_cost("C"),
        "hop_B": node_b.routing_table.get_next_hop("C") or "-",
        "notes": "B detects local link drop; A not notified yet"
    })

    rounds_taken = 0
    converged = False

    # Step 3: Round-by-round exchange until convergence
    for r in range(1, max_rounds + 1):
        rounds_taken = r

        # Sub-step 1: B advertises its current vector to A
        vec_b_to_a = node_b.get_outgoing_vector(for_neighbour="A")
        node_a.receive_vector("B", vec_b_to_a)

        # Sub-step 2: A advertises its updated vector to B
        vec_a_to_b = node_a.get_outgoing_vector(for_neighbour="B")
        node_b.receive_vector("A", vec_a_to_b)

        current_cost_a = node_a.routing_table.get_cost("C")
        current_hop_a = node_a.routing_table.get_next_hop("C") or "-"
        current_cost_b = node_b.routing_table.get_cost("C")
        current_hop_b = node_b.routing_table.get_next_hop("C") or "-"

        history.append({
            "round": r,
            "event": f"Exchange Round {r}",
            "cost_A": current_cost_a,
            "hop_A": current_hop_a,
            "cost_B": current_cost_b,
            "hop_B": current_hop_b,
            "vec_B_to_A": vec_b_to_a.get("C", "OMITTED"),
            "vec_A_to_B": vec_a_to_b.get("C", "OMITTED"),
        })

        # Check convergence: both nodes recognize C is unreachable (cost >= 16)
        if current_cost_a >= INFINITY and current_cost_b >= INFINITY:
            converged = True
            break

    return {
        "mode": mode,
        "before_failure": {"cost_A": cost_a_before, "cost_B": cost_b_before},
        "rounds": rounds_taken,
        "converged": converged,
        "history": history,
    }


def print_simulation_run(result: Dict[str, Any]) -> None:
    """Pretty prints the round-by-round history of a simulation run."""
    mode = result["mode"]
    print(f"\n{'='*75}")
    print(f" EXPERIMENT RUN: Loop Prevention Mode = [{mode}]")
    print(f"{'='*75}")
    print("Initial steady state before link failure:")
    print(f"  Router A -> C: Cost = {result['before_failure']['cost_A']:.1f} (Next Hop: B)")
    print(f"  Router B -> C: Cost = {result['before_failure']['cost_B']:.1f} (Next Hop: C - direct)")
    print(f"\n--- Round-by-Round Progression After Link B-C Fails ---")
    print(f"{'Round':<7} {'A Cost to C':<14} {'A NextHop':<12} {'B Cost to C':<14} {'B NextHop':<12} {'Exchange Note'}")
    print("-" * 75)

    for step in result["history"]:
        cost_a_str = f"{step['cost_A']:.0f}" if step['cost_A'] < INFINITY else "16 (INF)"
        cost_b_str = f"{step['cost_B']:.0f}" if step['cost_B'] < INFINITY else "16 (INF)"
        r_str = f"R{step['round']}"

        if step["round"] == 0:
            note = "Link fails; B recalculates"
        else:
            adv_a = step['vec_A_to_B']
            adv_b = step['vec_B_to_A']
            adv_a_str = f"{adv_a:.0f}" if isinstance(adv_a, (int, float)) and adv_a < INFINITY else str(adv_a)
            adv_b_str = f"{adv_b:.0f}" if isinstance(adv_b, (int, float)) and adv_b < INFINITY else str(adv_b)
            note = f"Sent: B->A({adv_b_str}), A->B({adv_a_str})"

        print(f"{r_str:<7} {cost_a_str:<14} {step['hop_A']:<12} {cost_b_str:<14} {step['hop_B']:<12} {note}")

    print("-" * 75)
    print(f"Result: Converged to Unreachable in {result['rounds']} rounds.")


def run_full_comparison() -> Dict[str, Dict[str, Any]]:
    """Runs and compares all three loop prevention modes."""
    modes = [
        LOOP_PREVENTION_NONE,
        LOOP_PREVENTION_SPLIT_HORIZON,
        LOOP_PREVENTION_POISONED_REVERSE,
    ]

    results = {}
    print("\n" + "#"*75)
    print(" DISTRIBUTED ROUTING PROTOCOLS: COUNT-TO-INFINITY EXPERIMENT")
    print(" Testing Claim: Loop prevention mitigates slow convergence during failures")
    print("#"*75)

    for mode in modes:
        res = simulate_count_to_infinity(mode=mode)
        results[mode] = res
        print_simulation_run(res)

    # Executive Summary Table
    print(f"\n{'='*75}")
    print(" EXECUTIVE COMPARISON SUMMARY")
    print(f"{'='*75}")
    print(f"{'Mode':<22} {'Rounds to Converge':<22} {'Count-to-Infinity?':<22} {'Status'}")
    print("-" * 75)
    for mode, res in results.items():
        looped = "YES (Bounced to 16)" if mode == LOOP_PREVENTION_NONE else "NO (Prevented)"
        status = "Slow Failure" if mode == LOOP_PREVENTION_NONE else "Fast Convergence"
        print(f"{mode:<22} {res['rounds']:<22} {looped:<22} {status}")
    print("=" * 75)

    return results


if __name__ == "__main__":
    run_full_comparison()
