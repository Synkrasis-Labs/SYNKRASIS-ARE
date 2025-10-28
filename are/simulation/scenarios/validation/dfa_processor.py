"""
DFA processing and state machine logic.

This module handles DFA generation, alphabet creation,
and state transition analysis for validation.
"""

import time
from copy import copy
from functools import reduce
from itertools import product

from are.simulation.tool_utils import OperationType

from .data_structures import (
    FunctionArgument,
    FunctionCall,
    Node,
    ToolInfo,
    Transition,
)
from .utils import symbol_generator


def generate_alphabet(
    expected_sequence: list[FunctionCall], tools: list[ToolInfo]
) -> dict[str, FunctionCall]:
    """
    Generate alphabet mapping symbols to function calls.

    Args:
        expected_sequence: Expected sequence of function calls
        tools: Available tools/functions

    Returns:
        Dictionary mapping symbols to function calls
    """
    gen = symbol_generator()
    used_tools = {
        tool.name: [
            *[
                func_call
                for func_call in expected_sequence
                if func_call.name == tool.name
            ]
        ]
        for tool in tools
    }

    alphabet = {}
    general_generated: list[str] = []

    # create symbols for each unique function call in expected sequence
    for _, func_calls in used_tools.items():
        for func_call in func_calls:
            char = next(gen)
            alphabet[char] = func_call

        # create the general version of this function call with excluded values
        for func_call in func_calls:
            if func_call.name in general_generated:
                continue

            general_char = next(gen)
            general_arguments = {}
            # skip if no arguments
            if not func_call.arguments:
                continue
            for arg_name, arg in func_call.arguments.items():
                excluded_vals = [
                    fc.arguments[arg_name].value
                    for fc in func_calls
                    if arg_name in fc.arguments
                    and fc.arguments[arg_name].value is not None
                ]
                general_arguments[arg_name] = FunctionArgument(
                    name=arg_name,
                    value=None,
                    excluded_values=list(set(excluded_vals)) if excluded_vals else None,
                    type=arg.type,
                )
            alphabet[general_char] = FunctionCall(
                name=func_call.name, arguments=general_arguments
            )
            general_generated.append(func_call.name)

    return alphabet


def generate_dfa(
    expected_sequence: list[FunctionCall],
    alphabet: dict[str, FunctionCall],
    tools: list[ToolInfo],
) -> list[Node]:
    """
    Generate DFA from expected sequence and alphabet.

    Args:
        expected_sequence: Expected sequence of function calls
        alphabet: Symbol to function call mapping
        tools: Available tools/functions

    Returns:
        List of DFA nodes representing the state machine
    """
    tool_types = {tool.name: tool.type for tool in tools}

    nodes = []
    nodes.append(
        Node("G0"),
    )

    for index, tool in enumerate(expected_sequence):
        nodes.append(
            Node(f"G{index + 1}"),
        )
    nodes[-1].is_final = True

    for index, node in enumerate(nodes):
        node.transitions = []
        expected_tool = (
            expected_sequence[index] if index < len(expected_sequence) else None
        )
        self_loop_transition = Transition(symbols=[], _from=node, _to=node)

        for i, tool_call in enumerate(alphabet.items()):
            symbol, tc = tool_call

            # evaluate what happens in this state if the function is called
            if expected_tool is not None and tc.name == expected_tool.name:
                # check if the arguments match
                if all(
                    expected_tool.arguments.get(arg_name).value  # type: ignore
                    == tc.arguments.get(arg_name).value  # type: ignore
                    for arg_name in expected_tool.arguments
                ):
                    node.transitions.append(
                        Transition(
                            symbols=[symbol],
                            _from=node,
                            # stay in the same node if last node
                            _to=nodes[index + 1] if index + 1 < len(nodes) else node,
                        )
                    )
                    continue

            # if the function is not the expected one, we need to self-loop if it
            # is a Read function
            if tool_types.get(tc.name) == OperationType.READ:
                self_loop_transition.symbols.append(symbol)

            # if last iteration then append the self-loop transition
            if i == len(alphabet) - 1 and self_loop_transition.symbols:
                node.transitions.append(self_loop_transition)

    return nodes


def get_node_read_onlys(node: Node) -> list[str]:
    """
    Get the read-only actions for a given node.

    Args:
        node: DFA node to analyze

    Returns:
        List of read-only symbols for the node
    """
    read_onlys: list[str] = []
    for t in node.transitions:
        if t._to == t._from:
            read_onlys.extend(t.symbols)
    return read_onlys


def convert_dfa_to_single_symbol_transitions(dfa: list[Node]) -> list[Node]:
    """
    Convert DFA transitions to have only one symbol per transition.

    Args:
        dfa: The DFA represented as a list of Nodes.

    Returns:
        DFA with single-symbol transitions
    """
    _dfa = copy(dfa)
    for node in _dfa:
        new_transitions = []
        for transition in node.transitions:
            for symbol in transition.symbols:
                new_transitions.append(
                    Transition(
                        symbols=[symbol], _from=transition._from, _to=transition._to
                    )
                )
        node.transitions = new_transitions
    return _dfa


def iterate_action_space(
    seq: list[str],
    dfa: list[Node],
    expected_sequence: list[str],
    max_perms: int = 2_500_000,
):
    """
    Iterate through possible action sequences in the DFA up to a maximum number of permutations.

    Args:
        seq: Current sequence of symbols.
        dfa: The DFA represented as a list of Nodes.
        expected_sequence: The expected sequence of function calls.
        max_perms: Maximum number of permutations to generate.

    Yields:
        Possible action sequences
    """
    # convert dfa to have one transition per symbol
    dfa = convert_dfa_to_single_symbol_transitions(dfa)

    current = dfa[0]  # Start at initial state
    next_state = None

    # collect read-onlys for each harmful function
    harmful_read_onlys: dict[int, list[str]] = {}
    for index, action in enumerate(seq):
        next_state = None

        for transition in current.transitions:
            # earlier convertion ensured one symbol per transition
            if transition.symbols[0] == action:
                next_state = transition._to
                break

        if next_state is None:
            # we are in fail state
            # this harmful function can change to these read-onlys
            harmful_read_onlys[index] = [*get_node_read_onlys(current), "REMOVE"]
            continue

        current = next_state

    # append steps left to reaching the final state based on the expected sequence
    new_current = dfa[0]
    break_off_point = None
    for index, action in enumerate(expected_sequence):
        if new_current == current:
            break_off_point = index
            break

        next_state = None

        for transition in new_current.transitions:
            if transition.symbols[0] == action:
                next_state = transition._to
                break

        if next_state is None:
            continue

        new_current = next_state

    if break_off_point is not None:
        seq.extend(expected_sequence[break_off_point:])

    # given the lists of read-onlys for each harmful function create all permutations
    # between the lists (pick 1 from each list every time)
    permutations = product(*harmful_read_onlys.values())
    permutations_num = reduce(
        lambda x, y: x * y, map(len, harmful_read_onlys.values()), 1
    )
    print(f"Total permutations to evaluate: {permutations_num}", flush=True)
    if max_perms and permutations_num > max_perms:
        raise StopIteration(f"Permutations: {permutations_num}")

    start = time.time()
    for index, perm in enumerate(permutations):
        sample_seq = seq.copy()
        to_remove = []
        for idx, val in zip(harmful_read_onlys.keys(), perm):
            if val == "REMOVE":
                to_remove.append(idx)
            else:
                sample_seq.insert(idx, val)
        for idx in sorted(to_remove, reverse=True):
            sample_seq.pop(idx)

        if not index % 100_000:
            elapsed = time.time() - start
            print(
                f"Evaluated {index}/{permutations_num} permutations. Elapsed time: {elapsed:.2f}s",
                flush=True,
            )
            eta = (elapsed / (index + 1)) * (permutations_num - index - 1)
            print(f"Estimated time remaining: {eta:.2f}s", flush=True)
            # break if it will take more than 5 minutes
            if eta > 300:
                print(
                    "Aborting permutation evaluation due to time constraints.",
                    flush=True,
                )
                break

        yield sample_seq


def simplify_and_mark(seq: list[str], dfa: list[Node]):
    """
    Simplify sequence and mark harmful actions.

    Args:
        seq: Sequence of symbols
        dfa: DFA nodes

    Returns:
        Tuple of (simplified_seq, marked_seq, fail_states)
    """
    dfa = convert_dfa_to_single_symbol_transitions(dfa)

    current = dfa[0]
    simplified_seq = []
    marked_seq = []

    fail_states = 0

    for idx, action in enumerate(seq):
        next_state = None

        for transition in current.transitions:
            if transition.symbols[0] == action:
                next_state = transition._to
                break

        if next_state is None:
            fail_states += 1
            simplified_seq.append(action)
            marked_seq.append("X")
            continue

        if not next_state.name == current.name:
            simplified_seq.append(action)
            marked_seq.append(action)

        current = next_state

    return simplified_seq, marked_seq, fail_states
