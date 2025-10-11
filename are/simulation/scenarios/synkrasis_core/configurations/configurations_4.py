from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.configurations import ConfigurationsApp
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.types import EventRegisterer


class CustomScenario(COREScenario):
    """
    @TODO: Update this docstring.
    """

    prompt: str | None = (
        "Set a configuration for 'timeout' to '30 minutes' under the 'security' category. Then update it to '15 minutes' and put 'process' as its category. Finally, verify the change by printing the config."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        """Initialize apps and populate with sample data"""

        agui = AgentUserInterface()
        configurations_app = ConfigurationsApp()  # already populated with default data

        # Store apps for scenario use
        self.apps = [
            agui,
            configurations_app,
        ]

    def build_events_flow(self) -> None:
        """Define the sequence of events that will occur during the scenario"""

        agui = self.get_typed_app(AgentUserInterface)
        configurations_app = self.get_typed_app(ConfigurationsApp)

        with EventRegisterer.capture_mode():
            # User event: User requests task creation
            event1 = agui.send_message_to_agent(
                content=self.prompt,
            ).depends_on(None, delay_seconds=2)
            oracle1 = (
                configurations_app.set_config("timeout", "30 minutes", "security")
                .oracle()
                .depends_on(event1, delay_seconds=2)
            )
            oracle2 = (
                configurations_app.update_config("timeout", "15 minutes", "process")
                .oracle()
                .depends_on(oracle1, delay_seconds=2)
            )
            oracle3 = (
                configurations_app.print_config("timeout")
                .oracle()
                .depends_on(oracle2, delay_seconds=2)
            )

        self.events = [
            event1,
            oracle1,
            oracle2,
            oracle3,
        ]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    # Run the scenario in oracle mode and validate the agent actions
    run_and_validate(CustomScenario())
