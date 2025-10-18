import glob
import importlib
import logging
import os

from are.simulation.scenarios.utils.registry import register_scenario

logger = logging.getLogger(__name__)


def register_scenarios_from_directory(
    directory_name: str,
    file_pattern: str = "*.py",
    class_name: str = "CustomScenario",
    base_module_path: str = "are.simulation.scenarios.synkrasis_core",
) -> None:
    """
    Dynamically import and register scenario classes from a directory.

    Args:
        directory_name: Name of the subdirectory containing scenario files
        file_pattern: Glob pattern to match files (default: "*.py")
        class_name: Name of the class to import from each module (default: "CustomScenario")
        base_module_path: Base module path for imports (default: "are.simulation.scenarios.synkrasis_core")
    """
    # Get the directory path
    scenarios_dir = os.path.join(os.path.dirname(__file__), directory_name)

    # Find all matching files
    scenario_files = glob.glob(os.path.join(scenarios_dir, file_pattern))

    # Import and register scenarios from each file
    for scenario_file in scenario_files:
        module_name = os.path.basename(scenario_file)[:-3]  # Remove .py extension

        # Skip __init__.py files
        if module_name == "__init__":
            continue

        # Import the module dynamically
        module_path = f"{base_module_path}.{directory_name}.{module_name}"
        try:
            module = importlib.import_module(module_path)

            # Get the specified class from the module
            if hasattr(module, class_name):
                scenario_class = getattr(module, class_name)

                # Register the scenario
                logger.info(f"Registering scenario from file: {scenario_file}")
                register_scenario(module_name)(scenario_class)
            else:
                logger.warning(f"No {class_name} class found in {module_name}")
        except ImportError as e:
            logger.error(f"Error importing {module_path}: {e}")
