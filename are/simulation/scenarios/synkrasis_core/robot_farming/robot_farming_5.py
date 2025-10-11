from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.robot_farming import RobotFarmingApp
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.types import EventRegisterer


class CustomScenario(COREScenario):
    """
    @TODO: Update this docstring.
    """

    prompt: str | None = (
        "Disengage safety. Report your current position, then navigate to the charging pad."
        "Recharge there and re-engage safety."
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
                robot_farming_app.sense_pose()
                .oracle()
                .depends_on(oracle1, delay_seconds=2)
            )
            oracle3 = (
                robot_farming_app.move_to(x=1.0, y=1.0, yaw=0.0)
                .oracle()
                .depends_on(oracle2, delay_seconds=2)
            )
            oracle4 = (
                robot_farming_app.recharge()
                .oracle()
                .depends_on(oracle3, delay_seconds=2)
            )
            oracle5 = (
                robot_farming_app.lock_safety_mode()
                .oracle()
                .depends_on(oracle4, delay_seconds=2)
            )

        self.events = [
            event1,
            oracle1,
            oracle2,
            oracle3,
            oracle4,
            oracle5,
        ]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    # Run the scenario in oracle mode and validate the agent actions
    run_and_validate(CustomScenario())
