from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.automation import AutomationApp
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.types import EventRegisterer


class CustomScenario(COREScenario):
    """
    @TODO: Update this docstring.
    """

    prompt: str | None = (
        "The house does in lockdown mode. Lock the doors, activate the alarm and turn off the lights in that order. Then, set the thermostat to 30 degrees and turn everything back on in the same order they were shut down."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        """Initialize apps and populate with sample data"""

        agui = AgentUserInterface()
        automation_app = AutomationApp()  # already populated with default data

        # setup functions
        automation_app.unlock_door()
        automation_app.turn_on_lights()

        # Store apps for scenario use
        self.apps = [
            agui,
            automation_app,
        ]

    def build_events_flow(self) -> None:
        """Define the sequence of events that will occur during the scenario"""

        agui = self.get_typed_app(AgentUserInterface)
        automation_app = self.get_typed_app(AutomationApp)

        with EventRegisterer.capture_mode():
            # User event: User requests task creation
            event1 = agui.send_message_to_agent(
                content=self.prompt,
            ).depends_on(None, delay_seconds=2)
            oracle1 = (
                automation_app.lock_door().oracle().depends_on(event1, delay_seconds=2)
            )
            oracle2 = (
                automation_app.activate_alarm()
                .oracle()
                .depends_on(oracle1, delay_seconds=2)
            )
            oracle3 = (
                automation_app.turn_off_lights()
                .oracle()
                .depends_on(oracle2, delay_seconds=2)
            )
            oracle4 = (
                automation_app.set_thermostat(temperature=30)
                .oracle()
                .depends_on(oracle3, delay_seconds=2)
            )
            oracle5 = (
                automation_app.unlock_door()
                .oracle()
                .depends_on(oracle4, delay_seconds=2)
            )
            oracle6 = (
                automation_app.deactivate_alarm()
                .oracle()
                .depends_on(oracle5, delay_seconds=2)
            )
            oracle7 = (
                automation_app.turn_on_lights()
                .oracle()
                .depends_on(oracle6, delay_seconds=2)
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
        ]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    # Run the scenario in oracle mode and validate the agent actions
    run_and_validate(CustomScenario())
