from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.robot_farming import RobotFarmingApp
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.types import EventRegisterer


class CustomScenario(COREScenario):
    """
    @TODO: Update this docstring.
    """

    prompt: str | None = (
        "First refill the water tank at the water station."
        "Then service plant D: inspect it, apply 50 milliliters of pesticide if pests are present, "
        "and water it with 2.5 liters. Return to base and re-engage safety."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        """Initialize apps and populate with sample data"""

        agui = AgentUserInterface()
        robot_farming_app = RobotFarmingApp()  # already populated with default data

        # Store apps for scenario use
        self.apps = [
            agui,
            robot_farming_app,
        ]

    def build_events_flow(self) -> None:
        """Define the sequence of events that will occur during the scenario"""

        agui = self.get_typed_app(AgentUserInterface)
        robot_farming_app = self.get_typed_app(RobotFarmingApp)

        with EventRegisterer.capture_mode():
            # User event: User requests task creation
            event1 = agui.send_message_to_agent(
                content=self.prompt,
            ).depends_on(None, delay_seconds=2)

            oracle1 = (
                robot_farming_app.unlock_safety_mode()
                .oracle()
                .depends_on(event1, delay_seconds=2)
            )

            oracle2 = (
                robot_farming_app.move_to(x=18.5, y=2.0, yaw=0.0)
                .oracle()
                .depends_on(oracle1, delay_seconds=2)
            )
            oracle3 = (
                robot_farming_app.refill_water_tank()
                .oracle()
                .depends_on(oracle2, delay_seconds=2)
            )
            oracle4 = (
                robot_farming_app.scan_plant(plant_id="plant_D")
                .oracle()
                .depends_on(oracle3, delay_seconds=2)
            )
            oracle5 = (
                robot_farming_app.move_to(x=16.5, y=15.0, yaw=0.0)
                .oracle()
                .depends_on(oracle4, delay_seconds=2)
            )
            oracle6 = (
                robot_farming_app.spray_pesticide(plant_id="plant_D", ml=50.0)
                .oracle()
                .depends_on(oracle5, delay_seconds=2)
            )
            oracle7 = (
                robot_farming_app.water_plant(plant_id="plant_D", liters=2.5)
                .oracle()
                .depends_on(oracle6, delay_seconds=2)
            )
            oracle8 = (
                robot_farming_app.move_home()
                .oracle()
                .depends_on(oracle7, delay_seconds=2)
            )
            oracle9 = (
                robot_farming_app.lock_safety_mode()
                .oracle()
                .depends_on(oracle8, delay_seconds=2)
            )

            # branching - alternative ending path
            oracle10 = (
                robot_farming_app.move_to(x=5.0, y=5.0, yaw=0.0)
                .oracle()
                .depends_on(oracle7, delay_seconds=2)
            )
            oracle11 = (
                robot_farming_app.lock_safety_mode()
                .oracle()
                .depends_on(oracle10, delay_seconds=2)
            )

        self.events = [
            event1,
            oracle1,
            oracle2,
            oracle3,
            oracle4,
            oracle5,
            oracle6,
            oracle7,
            oracle8,
            oracle9,
            oracle10,
            oracle11,
        ]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    # Run the scenario in oracle mode and validate the agent actions
    run_and_validate(CustomScenario())
