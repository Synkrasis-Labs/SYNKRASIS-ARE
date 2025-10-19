import time
from copy import copy
from dataclasses import dataclass, field
from functools import reduce
from itertools import product
from typing import Any, Callable

from are.simulation.apps.core_app import COREApp
from are.simulation.scenarios.scenario import Scenario
from are.simulation.scenarios.utils.dag_visualization import (
    visualize_dag_comparison,
)
from are.simulation.scenarios.validation_result import ScenarioValidationResult
from are.simulation.tool_utils import AppTool, OperationType
from are.simulation.types import OracleEvent


@dataclass
class Node:
    name: str
    transitions: list["Transition"] = field(default_factory=list)
    is_final: bool = False


@dataclass
class Transition:
    symbols: list[str]
    _from: Node
    _to: Node

    def __repr__(self):
        symbols_str = ", ".join(self.symbols)
        return f"Transition(on: [{symbols_str}] to: {self._to.name})"


@dataclass
class FunctionArgument:
    name: str
    value: Any | None
    excluded_values: list[Any] | None
    type: str


@dataclass
class FunctionCall:
    name: str
    arguments: dict[str, FunctionArgument]


@dataclass
class DAGNode:
    event_id: str
    event: OracleEvent
    dependencies: list[str]


@dataclass
class DAG:
    nodes: dict[str, DAGNode]
    adjacency_list: dict[str, list[str]]


@dataclass
class ToolInfo:
    name: str
    arguments: dict[str, str]  # argument name to type mapping
    type: OperationType


@dataclass
class InverseAlphabetEntry:
    symbol: str
    arguments: dict[str, FunctionArgument]


def symbol_generator():
    """Yields symbols: 'A', 'B', ..., 'Z', 'AA', 'AB', ..."""
    i = 0
    while True:
        s = ""
        n = i
        while True:
            s = chr(ord("A") + (n % 26)) + s
            n = n // 26 - 1
            if n < 0:
                break
        yield s
        i += 1


def LD(s1: list[str], s2: list[str], k_ins: int = 1, k_del: int = 1, k_sub: int = 1):
    m, n = len(s1), len(s2)
    # Initialize matrix of size (m+1) x (n+1)
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    # Initialize first row and column
    for i in range(m + 1):
        dp[i][0] = i * k_del
    for j in range(n + 1):
        dp[0][j] = j * k_ins

    # Fill the matrix
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s1[i - 1] == s2[j - 1]:
                cost = 0
            else:
                cost = k_sub
            dp[i][j] = min(
                dp[i - 1][j] + k_del,  # Deletion
                dp[i][j - 1] + k_ins,  # Insertion
                dp[i - 1][j - 1] + cost,  # Substitution
            )

    return dp[m][n]


def LD_norm(
    a: list[str],
    b: list[str],
    fail_states: int | None = None,
    k_ins: int = 1,
    k_del: int = 1,
    k_sub: int = 1,
) -> float:
    ld = (
        LD(a, b, k_ins=k_ins, k_del=k_del, k_sub=k_sub)
        if fail_states is None
        else fail_states
    )
    return (2 * ld) / (len(a) + len(b) + ld)


def path_correctness(
    a: list[str], b: list[str], k_ins: int = 1, k_del: int = 1, k_sub: int = 1
) -> float:
    return 1 - LD_norm(a, b, k_ins=k_ins, k_del=k_del, k_sub=k_sub)


def generate_alphabet(
    expected_sequence: list[FunctionCall], tools: list[ToolInfo]
) -> dict[str, FunctionCall]:
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
    """
    # convert dfa to have one transition per symbol
    dfa = convert_dfa_to_single_symbol_transitions(dfa)

    # debug
    # print(f"Converted DFA: {dfa}")

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

        # choose `max_perm` random permutations
        # permutations = random.sample(permutations, max_perms)

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


def generate_dag_paths(dag: DAG) -> list[list[FunctionCall]]:
    root_nodes = [
        node_id for node_id, node in dag.nodes.items() if not node.dependencies
    ]
    all_dependencies = set()
    for node in dag.nodes.values():
        all_dependencies.update(node.dependencies)
    leaf_nodes = [
        node_id for node_id in dag.nodes.keys() if node_id not in all_dependencies
    ]

    all_paths = []

    def find_paths(
        current_node: str, target_nodes: set, current_path: list, visited: set
    ):
        current_path.append(current_node)
        visited.add(current_node)

        if current_node in target_nodes:
            path_function_calls = []
            for event_id in current_path:
                event = dag.nodes[event_id].event
                arguments = {}

                function_name = extract_function_name_from_event_id(event_id)
                action_description = event.action_desc
                if action_description:
                    for arg in action_description.args:
                        arg_name = arg["name"]
                        arg_value = arg["value"]
                        arg_type = arg["value_type"]
                        arguments[arg_name] = FunctionArgument(
                            name=arg_name,
                            value=arg_value,
                            excluded_values=None,
                            type=arg_type if arg_value is not None else "NoneType",
                        )

                function_call = FunctionCall(name=function_name, arguments=arguments)
                path_function_calls.append(function_call)
            all_paths.append(path_function_calls)
        else:
            for child in dag.adjacency_list.get(current_node, []):
                if child not in visited:
                    find_paths(child, target_nodes, current_path, visited.copy())

        current_path.pop()

    leaf_nodes_set = set(leaf_nodes)
    for root in root_nodes:
        find_paths(root, leaf_nodes_set, [], set())

    return all_paths


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
    out_symbol = ""

    # keep only symbols that match the function name
    candidate_symbols = [
        symbol for symbol, fc in alphabet.items() if fc.name == func_call.name
    ]

    print(f"Candidate symbols for {func_call.name}: {candidate_symbols}", flush=True)

    if len(candidate_symbols) == 1:
        return candidate_symbols[0]

    # check non-general matches
    for symbol in candidate_symbols:
        # non-general candidates have a 1-1 match of arguments
        if all(
            func_call.arguments[arg_name].value
            == alphabet[symbol].arguments[arg_name].value
            for arg_name in func_call.arguments
        ):
            out_symbol = symbol
            break
        else:
            out_symbol = symbol

    return out_symbol


def simplify_and_mark(seq: list[str], dfa: list[Node]):
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


def core_algo(
    agent_sequence: list[str],
    expected_sequence: list[str],
    dfa: list[Node],
    distance_algos: list[Callable[[list[str], list[str]], float]],
):
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


class COREScenario(Scenario):
    prompt: str | None = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ensure prompt is set
        if self.prompt is None:
            raise ValueError("Scenario prompt must be set.")

        # filename = sys.modules[self.__class__.__module__].__file__
        # if not filename:
        #     raise Exception(
        #         "Could not determine module file for scenario registration."
        #     )

        # register_scenario(filename)(self.__class__)

    def validate(self, env) -> ScenarioValidationResult:
        """
        Validate that the scenario completed successfully.

        Check that the agent properly interacted with our custom app.
        """
        # Get core apps first
        if not self.apps:
            return ScenarioValidationResult(
                success=False,
                exception=Exception("No apps found in scenario."),
            )

        core_apps = [app for app in self.apps if isinstance(app, COREApp)]
        if not core_apps:
            return ScenarioValidationResult(
                success=False,
                exception=Exception("No COREApp instances found in scenario."),
            )

        # Get app names to filter events
        core_app_names = {app.__class__.__name__ for app in core_apps}

        # Filter events to only include those from COREApps
        core_events = []
        for event in self.events:
            event_id = event.event_id
            # Extract app name from event_id (format: ENV-AppName.function or AGENT-AppName.function)
            if "." in event_id:
                clean_id = event_id.replace("ENV-", "").replace("AGENT-", "")
                app_name = clean_id.split(".")[0]
                if app_name in core_app_names:
                    core_events.append(event)

        # Build DAG structure for validation using only core events
        nodes = {}
        adjacency_list = {}

        for event in core_events:
            # Filter dependencies to only include other core events
            filtered_deps = []
            for dep in event.dependencies:
                dep_id = dep.event_id
                if "." in dep_id:
                    clean_dep_id = dep_id.replace("ENV-", "").replace("AGENT-", "")
                    dep_app_name = clean_dep_id.split(".")[0]
                    if dep_app_name in core_app_names:
                        filtered_deps.append(dep.event_id)

            nodes[event.event_id] = DAGNode(
                event_id=event.event_id,
                event=event,
                dependencies=filtered_deps,
            )
            adjacency_list[event.event_id] = []

        for event in core_events:
            for dep in event.dependencies:
                if dep.event_id in nodes:  # Only add if dependency is also a core event
                    adjacency_list[dep.event_id].append(event.event_id)

        dag = DAG(nodes=nodes, adjacency_list=adjacency_list)

        event_order = []
        dag_dict = {}
        for event in core_events:
            dag_dict[event.event_id] = nodes[event.event_id].dependencies
            event_order.append(event.event_id)

        # Validate DAG execution order
        completed_events = env.event_log.list_view()
        print(f"Completed events: {completed_events}", flush=True)

        # Visualize both expected and actual execution
        visualize_dag_comparison(dag_dict, core_events, completed_events)

        core_apps = [app for app in self.apps if isinstance(app, COREApp)]
        tools = reduce(lambda x, y: x + y, [app.get_tools() for app in core_apps])
        tool_infos = extract_tool_names(tools)
        expected_sequences = generate_dag_paths(dag)
        agent_sequence = parse_agent_output(completed_events, tool_infos)

        print("Expected sequences:", expected_sequences, flush=True)
        print("Agent sequence:", agent_sequence, flush=True)

        distance_algos: list[Callable[[list[str], list[str]], float]] = [
            path_correctness
        ]

        best_distances_all: list[dict[str, float]] = []
        best_sequences_all: list[dict[str, None | list[str]]] = []

        for i, seq in enumerate(expected_sequences):
            # symbol -> FunctionCall

            alphabet = generate_alphabet(seq, tool_infos)
            dfa = generate_dfa(seq, alphabet, tool_infos)

            # Visualize the alphabet and DFA for this sequence
            visualize_alphabet_and_dfa(i, seq, alphabet, dfa)

            print(dfa, flush=True)

            # convert agent sequence to symbols
            agent_symbols = [fc2symbol(fc, alphabet) for fc in agent_sequence]
            seq_symbols = [fc2symbol(fc, alphabet) for fc in seq]
            print(f"Agent symbols: {agent_symbols}", flush=True)
            print(f"Expected symbols: {seq_symbols}", flush=True)

            # debug - shuffle some symbols in agent_symbols to simulate errors
            # import random

            # if len(agent_symbols) >= 2:
            #     idx1, idx2 = random.sample(range(len(agent_symbols)), 2)
            #     agent_symbols[idx1], agent_symbols[idx2] = (
            #         agent_symbols[idx2],
            #         agent_symbols[idx1],
            #     )
            # print(f"Shuffled Agent symbols: {agent_symbols}", flush=True)

            # run core search
            best_sequences, best_distances = core_algo(
                agent_sequence=agent_symbols,
                expected_sequence=seq_symbols,
                dfa=dfa,
                distance_algos=distance_algos,
            )

            print(f"Best distances: {best_distances}", flush=True)
            print(f"Best sequences: {best_sequences}", flush=True)

            best_distances_all.append(best_distances)
            best_sequences_all.append(best_sequences)

        # print best distance for each algo
        for algo, distances in zip(distance_algos, best_distances_all):
            print(f"\n=== Distance Algorithm: {algo.__name__} ===", flush=True)
            for seq_index, distance_dict in enumerate(best_distances_all):
                distance = distance_dict[algo.__name__]
                best_seq = best_sequences_all[seq_index][algo.__name__]
                print(
                    f"Sequence {seq_index + 1}: Best Distance = {distance:.4f}, Best Sequence = {best_seq}",
                    flush=True,
                )

        return ScenarioValidationResult(
            success=False,
            exception=Exception("Validation not implemented yet"),
        )
