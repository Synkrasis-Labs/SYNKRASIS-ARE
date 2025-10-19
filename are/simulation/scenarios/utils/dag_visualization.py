# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

"""
DAG Visualization Utilities

This module provides utilities for visualizing Directed Acyclic Graphs (DAGs)
of events in scenarios, showing both expected event flow and actual execution.
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from are.simulation.scenarios.core_scenario import FunctionCall, Node


def extract_function_name(event_id: str) -> str:
    """Extract just the function name from the full event ID."""
    # Format is typically: ENV-AppName.function_name-uuid
    if "." in event_id and "-" in event_id:
        # Split by '-' and take the part with the dot
        parts = event_id.split("-")
        for part in parts:
            if "." in part:
                return part.split(".")[-1]
    return event_id  # fallback to full ID if parsing fails


def get_event_args_from_dag(events: list, event_id: str) -> dict:
    """Extract arguments for an event from the scenario's events list."""
    for event in events:
        if event.event_id == event_id:
            # Handle different event types
            action = getattr(event, "action", None)
            if action:
                # For Event objects
                return getattr(action, "args", {})

            action_desc = getattr(event, "action_desc", None)
            if action_desc:
                # For OracleEvent objects
                args_dict = {}
                args_list = getattr(action_desc, "args", [])
                for arg in args_list:
                    if isinstance(arg, dict):
                        args_dict[arg.get("name", "unknown")] = arg.get("value", "")
                return args_dict
    return {}


def get_completed_event_args(completed_event: Any) -> dict:
    """Extract arguments from a completed event."""
    if hasattr(completed_event, "get_args"):
        return completed_event.get_args()
    elif hasattr(completed_event, "action") and completed_event.action:
        if hasattr(completed_event.action, "args"):
            return completed_event.action.args
        elif hasattr(completed_event.action, "resolved_args"):
            return completed_event.action.resolved_args or {}
    return {}


def format_args(args: dict) -> str:
    """Format function arguments for display."""
    if not args:
        return "()"

    formatted_args = []
    for key, value in args.items():
        if key == "self":  # Skip 'self' parameter
            continue

        if isinstance(value, str):
            # Truncate long strings
            if len(value) > 30:
                formatted_args.append(f"{key}='{value[:27]}...'")
            else:
                formatted_args.append(f"{key}='{value}'")
        elif isinstance(value, dict) and "value" in value:
            # Handle parameter dict format from scenario events
            val = value["value"]
            if isinstance(val, str) and len(val) > 30:
                formatted_args.append(f"{key}='{val[:27]}...'")
            else:
                formatted_args.append(f"{key}={val}")
        else:
            formatted_args.append(f"{key}={value}")

    return f"({', '.join(formatted_args)})"


def visualize_expected_dag(dag: dict, events: list):
    """Visualize the expected DAG structure."""
    print("\n" + "=" * 70)
    print("EXPECTED DAG STRUCTURE (Build Events Flow)")
    print("=" * 70)

    # Create a mapping from full IDs to function names
    id_to_func = {event_id: extract_function_name(event_id) for event_id in dag.keys()}

    # Find root nodes (no dependencies)
    root_nodes = [event_id for event_id, deps in dag.items() if not deps]

    # Print the DAG structure
    print("\nExpected Event Flow:")
    print("-" * 50)

    visited = set()

    def print_node(event_id: str, level: int = 0, prefix: str = ""):
        if event_id in visited:
            return
        visited.add(event_id)

        func_name = id_to_func[event_id]
        args = get_event_args_from_dag(events, event_id)
        args_str = format_args(args)
        indent = "  " * level
        print(f"{indent}{prefix}{func_name}{args_str}")

        # Find children (events that depend on this one)
        children = [eid for eid, deps in dag.items() if event_id in deps]

        for i, child in enumerate(children):
            is_last = i == len(children) - 1
            child_prefix = "└── " if is_last else "├── "
            print_node(child, level + 1, child_prefix)

    # Print from root nodes
    for i, root in enumerate(root_nodes):
        if i > 0:
            print()  # Add spacing between root trees
        print_node(root)

    print(f"\nTotal Expected Events: {len(dag)}")
    print("=" * 70 + "\n")


def visualize_actual_execution(completed_events: list):
    """Visualize the actual execution path."""
    print("=" * 70)
    print("ACTUAL EXECUTION PATH (Environment Event Log)")
    print("=" * 70)

    if not completed_events:
        print("\nNo events have been executed yet.")
        print("=" * 70 + "\n")
        return

    print("\nActual Execution Timeline:")
    print("-" * 50)

    # Group events by type for better visualization
    event_types = {}
    for event in completed_events:
        event_type = str(event.event_type)
        if event_type not in event_types:
            event_types[event_type] = []
        event_types[event_type].append(event)

    # Sort events by time
    sorted_events = sorted(completed_events, key=lambda e: e.event_time)

    for i, event in enumerate(sorted_events):
        func_name = extract_function_name(event.event_id)
        event_type = str(event.event_type)
        timestamp = f"{event.event_time:.1f}s"

        # Get and format arguments
        args = get_completed_event_args(event)
        args_str = format_args(args)

        # Show status based on success/failure
        if hasattr(event, "metadata") and event.metadata:
            if hasattr(event.metadata, "exception") and event.metadata.exception:
                status = "❌ FAILED"
            else:
                status = "✅ SUCCESS"
        else:
            status = "✅ SUCCESS"

        # Show connection to previous event
        if i > 0:
            print("│")

        print(f"├── [{timestamp}] {func_name}{args_str} ({event_type}) {status}")

    # Summary of actual execution
    print("\n" + "-" * 50)
    print("Execution Summary:")
    print(f"Total Executed Events: {len(completed_events)}")

    # Count by event type
    type_counts = {}
    success_count = 0
    failed_count = 0

    for event in completed_events:
        event_type = str(event.event_type)
        type_counts[event_type] = type_counts.get(event_type, 0) + 1

        # Count successes/failures
        if hasattr(event, "metadata") and event.metadata:
            if hasattr(event.metadata, "exception") and event.metadata.exception:
                failed_count += 1
            else:
                success_count += 1
        else:
            success_count += 1

    for event_type, count in type_counts.items():
        print(f"  {event_type}: {count} events")

    print(f"Successful: {success_count}")
    print(f"Failed: {failed_count}")

    # Time span
    if len(completed_events) > 1:
        start_time = min(e.event_time for e in completed_events)
        end_time = max(e.event_time for e in completed_events)
        duration = end_time - start_time
        print(f"Execution Duration: {duration:.1f}s")

    print("=" * 70 + "\n")


def visualize_dag_comparison(dag: dict, events: list, completed_events: list):
    """
    Visualize both expected DAG and actual execution for comparison.

    Args:
        dag: Dictionary representing the expected DAG structure
        events: List of scenario events (for extracting expected arguments)
        completed_events: List of completed events from environment
    """
    visualize_expected_dag(dag, events)
    visualize_actual_execution(completed_events)


def visualize_alphabet_and_dfa(
    sequence_index: int,
    expected_sequence: list["FunctionCall"],
    alphabet: dict[str, "FunctionCall"],
    dfa: list["Node"],
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
            # Group transitions by target state for cleaner display
            transitions_by_target = {}
            for transition in node.transitions:
                target = transition._to.name
                if target not in transitions_by_target:
                    transitions_by_target[target] = []
                transitions_by_target[target].extend(transition.symbols)

            for target_state, symbols in transitions_by_target.items():
                if symbols:  # Only show transitions with symbols
                    symbols_str = ", ".join(sorted(symbols))
                    arrow = "→" if target_state != node.name else "↻"
                    print(f"    {arrow} {target_state} on: {symbols_str}")
                elif target_state == node.name:
                    # Self-loop with no symbols (shouldn't happen, but just in case)
                    print(f"    ↻ {target_state} (no symbols)")
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
