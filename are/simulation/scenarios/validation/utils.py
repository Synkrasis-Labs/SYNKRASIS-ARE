"""
Utility functions for validation.

This module contains helper functions for parsing, conversion,
and file I/O operations used throughout the validation system.
"""

import json
import os
from datetime import datetime
from typing import Callable

from are.simulation.tool_utils import AppTool, OperationType

from .data_structures import FunctionArgument, FunctionCall, ToolInfo


def symbol_generator():
    """Yields symbols: 'A', 'B', ..., 'Z', 'AA', 'AB', ... skipping 'X'"""
    i = 0
    while True:
        s = ""
        n = i
        while True:
            s = chr(ord("A") + (n % 26)) + s
            if s == "X":
                s = chr(ord("A") + ((n + 1) % 26)) + s[1:]  # skip 'X'
            n = n // 26 - 1
            if n < 0:
                break
        yield s
        i += 1


def extract_function_name_from_event_id(event_id: str) -> str:
    """Extract function name from event_id format like 'ENV-AppName.function_name-uuid'."""
    if "_" in event_id:
        clean_id = event_id.replace("ENV-", "").replace("AGENT-", "")
        if "." in clean_id:
            function_part = clean_id.split(".")[-1]  # Get part after the last dot
        else:
            function_part = clean_id.split("_")[0]
    else:
        function_part = event_id

    # Remove UUID suffix - everything after the first hyphen in the function name
    if "-" in function_part:
        function_part = function_part.split("-")[0]

    return function_part


def extract_tool_names(tools: list[AppTool]) -> list[ToolInfo]:
    """Extract ToolInfo objects by removing app class name prefix from tool names."""
    tool_infos = list()
    for tool in tools:
        # Remove app class name prefix (e.g., "ConfigurationsApp__set_config" -> "set_config")
        if "__" in tool.name:
            clean_name = tool.name.split("__", 1)[1]  # Take everything after first "__"
        else:
            clean_name = tool.name

        # Build arguments dict from AppTool.args
        arguments = {arg.name: arg.arg_type for arg in tool.args}

        tool_info = ToolInfo(
            name=clean_name,
            arguments=arguments,
            type=OperationType.WRITE if tool.write_operation else OperationType.READ,
        )
        tool_infos.append(tool_info)
    return tool_infos


def parse_agent_output(
    completed_events, tool_infos: list[ToolInfo]
) -> list[FunctionCall]:
    """Parse completed events into FunctionCall format matching expected sequences."""
    agent_sequence = []

    for event in completed_events:
        event_id = event.event_id
        function_name = extract_function_name_from_event_id(event_id)

        # Check if this function matches any available tool
        if function_name not in {info.name for info in tool_infos}:
            continue  # Skip this event if function not in tools

        # Extract arguments from event action, excluding 'self'
        arguments = {}
        for arg_name, arg_value in event.action.args.items():
            if arg_name != "self":  # Skip 'self' parameter
                arguments[arg_name] = FunctionArgument(
                    name=arg_name,
                    value=arg_value,
                    excluded_values=None,
                    type=type(arg_value).__name__
                    if arg_value is not None
                    else "NoneType",
                )

        function_call = FunctionCall(name=function_name, arguments=arguments)

        agent_sequence.append(function_call)

    return agent_sequence


def fc2symbol(func_call: FunctionCall, alphabet: dict[str, FunctionCall]) -> str:
    """
    Convert function call to corresponding symbol in alphabet.

    Args:
        func_call: Function call to convert
        alphabet: Symbol to function call mapping

    Returns:
        Corresponding symbol
    """
    out_symbol = ""

    # keep only symbols that match the function name
    candidate_symbols = [
        symbol for symbol, fc in alphabet.items() if fc.name == func_call.name
    ]

    if len(candidate_symbols) == 1:
        return candidate_symbols[0]

    # check non-general matches
    for symbol in candidate_symbols:
        # non-general candidates have a 1-1 match of arguments
        check = all(
            str(func_call.arguments[arg_name].value)
            == str(alphabet[symbol].arguments[arg_name].value)
            for arg_name in func_call.arguments
        )
        if check:
            out_symbol = symbol
            break
        else:
            # this works because we are guaranteed only one general symbol per function
            # and that general symbols are last in the candidate_symbols list
            out_symbol = symbol

    return out_symbol


def serialize_function_call(func_call: FunctionCall) -> dict:
    """Serialize a FunctionCall object to dictionary for JSON output."""
    return {
        "name": func_call.name,
        "arguments": {
            arg_name: {
                "name": arg.name,
                "value": arg.value,
                "excluded_values": arg.excluded_values,
                "type": arg.type,
            }
            for arg_name, arg in func_call.arguments.items()
        },
    }


def save_evaluation_results(
    scenario_name: str,
    expected_sequences: list[list[FunctionCall]],
    agent_sequence: list[FunctionCall],
    expected_symbol_sequences: list[list[str]],
    agent_symbol_sequence: list[str],
    best_distances_all: list[dict[str, float]],
    best_sequences_all: list[dict[str, None | list[str]]],
    harmful_rates_all: list[float],
    prefix_criticalities_all: list[float | None],
    efficiencies_all: list[float | None],
    distance_algos: list[Callable],
    output_dir: str = "evaluation_results",
) -> str:
    """Save evaluation results to JSON file."""
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Prepare the data structure
    evaluation_data = {
        "scenario_name": scenario_name,
        "timestamp": datetime.now().isoformat(),
        "expected_sequences": [
            [serialize_function_call(fc) for fc in seq] for seq in expected_sequences
        ],
        "agent_sequence": [serialize_function_call(fc) for fc in agent_sequence],
        "expected_symbol_sequences": expected_symbol_sequences,
        "agent_symbol_sequence": agent_symbol_sequence,
        "distance_algorithms": [algo.__name__ for algo in distance_algos],
        "sequences": [],
        "summary": {
            "total_sequences": len(expected_sequences),
            "avg_harmful_rate": sum(harmful_rates_all) / len(harmful_rates_all)
            if harmful_rates_all
            else 0,
            "avg_efficiency": sum(e for e in efficiencies_all if e is not None)
            / len([e for e in efficiencies_all if e is not None])
            if any(e is not None for e in efficiencies_all)
            else None,
            "avg_prefix_criticality": sum(
                p for p in prefix_criticalities_all if p is not None
            )
            / len([p for p in prefix_criticalities_all if p is not None])
            if any(p is not None for p in prefix_criticalities_all)
            else None,
        },
    }

    # Add per-sequence results
    for seq_index in range(len(expected_sequences)):
        sequence_data = {
            "sequence_index": seq_index + 1,
            "expected_symbol_sequence": expected_symbol_sequences[seq_index],
            "agent_symbol_sequence": agent_symbol_sequence,
            "distance_metrics": {},
            "harmful_rate": harmful_rates_all[seq_index],
            "prefix_criticality": prefix_criticalities_all[seq_index],
            "efficiency": efficiencies_all[seq_index],
        }

        # Add distance algorithm results
        for algo in distance_algos:
            sequence_data["distance_metrics"][algo.__name__] = {
                "best_distance": best_distances_all[seq_index][algo.__name__],
                "best_sequence": best_sequences_all[seq_index][algo.__name__],
            }

        evaluation_data["sequences"].append(sequence_data)

    # Add algorithm-specific averages to summary
    for algo in distance_algos:
        avg_distance = sum(
            best_distances_all[i][algo.__name__] for i in range(len(expected_sequences))
        ) / len(expected_sequences)
        evaluation_data["summary"][f"avg_{algo.__name__}_distance"] = avg_distance

    # Save to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{scenario_name}_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w") as f:
        json.dump(evaluation_data, f, indent=2, default=str)

    return filepath
