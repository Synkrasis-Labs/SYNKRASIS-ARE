"""
Validation module for CORE scenarios.

This module provides structured validation components for analyzing
agent behavior against expected sequences using various algorithms
and metrics.
"""

from .dag_processor import (
    generate_dag_paths,
    visualize_dag_comparison,
)
from .data_structures import (
    DAG,
    DAGNode,
    FunctionArgument,
    FunctionCall,
    InverseAlphabetEntry,
    Node,
    ToolInfo,
    Transition,
)
from .dfa_processor import (
    convert_dfa_to_single_symbol_transitions,
    generate_alphabet,
    generate_dfa,
    get_node_read_onlys,
    iterate_action_space,
    simplify_and_mark,
)
from .evaluation_coordinator import (
    core_algo,
    visualize_alphabet_and_dfa,
)
from .metrics import (
    LD,
    LD_norm,
    ktc,
    nw_ktc,
    path_correctness,
    prefix_criticality_score,
)
from .utils import (
    extract_function_name_from_event_id,
    extract_tool_names,
    fc2symbol,
    parse_agent_output,
    save_evaluation_results,
    serialize_function_call,
    symbol_generator,
)

__all__ = [
    # Data structures
    "Node",
    "Transition",
    "FunctionArgument",
    "FunctionCall",
    "DAGNode",
    "DAG",
    "ToolInfo",
    "InverseAlphabetEntry",
    # DAG processing
    "generate_dag_paths",
    "visualize_dag_comparison",
    # DFA processing
    "generate_alphabet",
    "generate_dfa",
    "convert_dfa_to_single_symbol_transitions",
    "iterate_action_space",
    "get_node_read_onlys",
    "simplify_and_mark",
    # Metrics
    "LD",
    "LD_norm",
    "path_correctness",
    "ktc",
    "nw_ktc",
    "prefix_criticality_score",
    # Utilities
    "symbol_generator",
    "extract_function_name_from_event_id",
    "extract_tool_names",
    "parse_agent_output",
    "fc2symbol",
    "serialize_function_call",
    "save_evaluation_results",
    # Evaluation coordination
    "core_algo",
    "visualize_alphabet_and_dfa",
]
