from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.configurations import ConfigurationsApp
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.types import EventRegisterer


class CustomScenario(COREScenario):
    """
    @TODO: Update this docstring.
    """

    prompt: str | None = (
        "Print the configuration for 'theme' and update it to 'light mode' while keeping the category unchanged."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        """Initialize apps and populate with sample data"""

        agui = AgentUserInterface()
        configurations_app = ConfigurationsApp()  # already populated with default data

        # setup functions
        configurations_app.set_config(
            "theme", "dark mode", "UI", "2025-02-12T10:00:00."
        )

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
                configurations_app.print_config("theme")
                .oracle()
                .depends_on(event1, delay_seconds=2)
            )
            oracle2 = (
                configurations_app.update_config("theme", "light mode")
                .oracle()
                .depends_on(oracle1, delay_seconds=2)
            )

        self.events = [
            event1,
            oracle1,
            oracle2,
        ]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    # Run the scenario in oracle mode and validate the agent actions
    run_and_validate(CustomScenario())
