"""
Evaluation coordinator for CORE scenario validation.

This module orchestrates the validation process, coordinating
between different components to evaluate agent performance.
"""

from typing import Callable

from .data_structures import FunctionCall, Node
from .dfa_processor import iterate_action_space, simplify_and_mark


def core_algo(
    agent_sequence: list[str],
    expected_sequence: list[str],
    dfa: list[Node],
    distance_algos: list[Callable[[list[str], list[str]], float]],
):
    """
    Core algorithm for evaluating agent sequence against expected sequence.

    Args:
        agent_sequence: Agent's actual sequence of symbols
        expected_sequence: Expected sequence of symbols
        dfa: DFA nodes representing the state machine
        distance_algos: List of distance algorithms to use

    Returns:
        Tuple of (best_sequences, best_distances)
    """
    # get the simplified (state-space transformed) agent sequence
    # and the marked sequence
    simpl, mark, _ = simplify_and_mark(agent_sequence, dfa)

    metrics = {}
    for algo in distance_algos:
        distance = algo(simpl, expected_sequence)
        metrics[algo.__name__] = distance

    # search action space for closer (distance) sequence
    # based on distance algos given
    best_distances: dict[str, float] = {algo.__name__: 0.0 for algo in distance_algos}
    best_sequences: dict[str, None | list[str]] = {
        algo.__name__: None for algo in distance_algos
    }

    for seq in iterate_action_space(mark, dfa, expected_sequence):
        for algo in distance_algos:
            dist = algo(simpl, seq)

            if dist > best_distances[algo.__name__]:
                best_distances[algo.__name__] = dist
                best_sequences[algo.__name__] = seq

    return best_sequences, best_distances


def visualize_alphabet_and_dfa(
    sequence_index: int,
    expected_sequence: list[FunctionCall],
    alphabet: dict[str, FunctionCall],
    dfa: list[Node],
):
    """
    Visualize the generated alphabet and DFA for a given expected sequence.

    Args:
        sequence_index: Index of the expected sequence being processed
        expected_sequence: The expected sequence of function calls
        alphabet: Dictionary of symbols to function calls
        dfa: List of DFA nodes
    """
    print("\n" + "=" * 80)
    print(f"ALPHABET AND DFA VISUALIZATION - Sequence {sequence_index + 1}")
    print("=" * 80)

    # Visualize Expected Sequence
    print("\n📋 Expected Sequence:")
    print("-" * 50)
    for i, func_call in enumerate(expected_sequence):
        args_str = ", ".join(
            [f"{arg_name}={arg.value}" for arg_name, arg in func_call.arguments.items()]
        )
        print(f"  {i + 1}. {func_call.name}({args_str})")

    # Visualize Alphabet
    print(f"\n🔤 Generated Alphabet ({len(alphabet)} symbols):")
    print("-" * 50)
    for symbol, func_call in alphabet.items():
        # Format arguments for display
        args_parts = []
        for arg_name, arg in func_call.arguments.items():
            if arg.value is not None:
                args_parts.append(f"{arg_name}={arg.value}")
            elif arg.excluded_values:
                excluded_str = ", ".join([str(v) for v in arg.excluded_values[:3]])
                if len(arg.excluded_values) > 3:
                    excluded_str += "..."
                args_parts.append(f"{arg_name}=* (excluded: {excluded_str})")
            else:
                args_parts.append(f"{arg_name}=*")

        args_str = ", ".join(args_parts) if args_parts else ""
        print(f"  {symbol}: {func_call.name}({args_str})")

    # Visualize DFA
    print(f"\n🤖 Generated DFA ({len(dfa)} states):")
    print("-" * 50)

    for node in dfa:
        state_marker = "🎯" if node.is_final else "⚪"
        print(f"  {state_marker} State: {node.name}")

        if node.transitions:
            print(f"  Transitions: {node.transitions}")
            for transition in node.transitions:
                target_state = transition._to.name
                symbols = transition.symbols
                if symbols:  # Only show transitions with symbols
                    symbols_str = ", ".join(sorted(symbols))
                    arrow = "→" if target_state != node.name else "↻"
                    print(f"    {arrow} {target_state} on: {symbols_str}")
                elif target_state == node.name:
                    symbols_str = ", ".join(sorted(symbols))
                    # Self-loop with no symbols (shouldn't happen, but just in case)
                    print(f"    ↻ {target_state} on: {symbols_str}")

        else:
            print("    (no transitions)")
        print()

    # DFA Analysis
    print("📊 DFA Analysis:")
    print("-" * 30)
    final_states = [node for node in dfa if node.is_final]
    print(f"  Total States: {len(dfa)}")
    print(
        f"  Final States: {len(final_states)} ({', '.join([s.name for s in final_states])})"
    )
    print(f"  Expected Sequence Length: {len(expected_sequence)}")

    # Check if DFA structure makes sense
    if len(dfa) == len(expected_sequence) + 1:
        print("  ✅ DFA has correct number of states (sequence length + 1)")
    else:
        print(f"  ⚠️  Expected {len(expected_sequence) + 1} states, got {len(dfa)}")

    print("=" * 80 + "\n")
