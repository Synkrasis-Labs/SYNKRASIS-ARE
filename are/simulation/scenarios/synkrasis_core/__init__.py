from are.simulation.scenarios.synkrasis_core.utils import (
    register_scenarios_from_directory,
)

# register automation scenarios
register_scenarios_from_directory("automation_scenarios", "automation_*.py")
register_scenarios_from_directory("communication_scenarios", "communication_*.py")
register_scenarios_from_directory("computations_scenarios", "computations_*.py")
register_scenarios_from_directory("configurations_scenarios", "configurations_*.py")
register_scenarios_from_directory("crud_scenarios", "crud_*.py")
register_scenarios_from_directory("desktop_manager_scenarios", "desktop_manager_*.py")
register_scenarios_from_directory("events_scheduler_scenarios", "events_scheduler_*.py")
register_scenarios_from_directory("file_management_scenarios", "file_management_*.py")
register_scenarios_from_directory("legal_compliance_scenarios", "legal_compliance_*.py")
register_scenarios_from_directory("navigation_scenarios", "navigation_*.py")
register_scenarios_from_directory("robot_arm_scenarios", "robot_arm_*.py")
register_scenarios_from_directory("robot_farming_scenarios", "robot_farming_*.py")
register_scenarios_from_directory("transactions_scenarios", "transactions_*.py")
register_scenarios_from_directory("validation_scenarios", "validation_*.py")
register_scenarios_from_directory("web_browsing_scenarios", "web_browsing_*.py")
register_scenarios_from_directory("writing_scenarios", "writing_*.py")
