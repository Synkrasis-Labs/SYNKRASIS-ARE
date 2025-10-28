"""
Data structures for CORE scenario validation.

This module contains all the dataclasses and type definitions
used throughout the validation system.
"""

from dataclasses import dataclass, field
from typing import Any

from are.simulation.tool_utils import OperationType
from are.simulation.types import OracleEvent


@dataclass
class Node:
    """Represents a state in the DFA."""

    name: str
    transitions: list["Transition"] = field(default_factory=list)
    is_final: bool = False


@dataclass
class Transition:
    """Represents a transition between DFA states."""

    symbols: list[str]
    _from: Node
    _to: Node

    def __repr__(self):
        symbols_str = ", ".join(self.symbols)
        return f"Transition(on: [{symbols_str}] to: {self._to.name})"


@dataclass
class FunctionArgument:
    """Represents an argument to a function call."""

    name: str
    value: Any | None
    excluded_values: list[Any] | None
    type: str


@dataclass
class FunctionCall:
    """Represents a function call with arguments."""

    name: str
    arguments: dict[str, FunctionArgument]


@dataclass
class DAGNode:
    """Represents a node in the DAG."""

    event_id: str
    event: OracleEvent
    dependencies: list[str]


@dataclass
class DAG:
    """Represents a Directed Acyclic Graph."""

    nodes: dict[str, DAGNode]
    adjacency_list: dict[str, list[str]]


@dataclass
class ToolInfo:
    """Information about a tool/function."""

    name: str
    arguments: dict[str, str]  # argument name to type mapping
    type: OperationType


@dataclass
class InverseAlphabetEntry:
    """Entry in the inverse alphabet mapping."""

    symbol: str
    arguments: dict[str, FunctionArgument]
