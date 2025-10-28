"""
DAG processing and analysis functionality.

This module handles DAG path generation and visualization
for scenario validation.
"""

from .data_structures import DAG, FunctionArgument, FunctionCall
from .utils import extract_function_name_from_event_id


def generate_dag_paths(dag: DAG) -> list[list[FunctionCall]]:
    """
    Generate all possible paths through the DAG from root to leaf nodes.

    Args:
        dag: The DAG to process

    Returns:
        List of all possible execution paths as sequences of FunctionCalls
    """
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


def visualize_dag_comparison(dag_dict, core_events, completed_events):
    """
    Visualize comparison between expected DAG and actual execution.

    This is a placeholder for the actual visualization functionality
    which should be imported from the existing utils module.

    Args:
        dag_dict: Dictionary representation of the DAG
        core_events: Expected core events
        completed_events: Actually completed events
    """
    # Import the actual visualization function
    from are.simulation.scenarios.utils.dag_visualization import (
        visualize_dag_comparison,
    )

    return visualize_dag_comparison(dag_dict, core_events, completed_events)
