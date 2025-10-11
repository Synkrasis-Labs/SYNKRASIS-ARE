from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.configurations import ConfigurationsApp
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.types import EventRegisterer


class CustomScenario(COREScenario):
    """
    @TODO: Update this docstring.
    """

    prompt: str | None = (
        "Set configurations for 'max-connections' to '100' in 'network', 'log-level' to 'debug' in 'system' with whatever order you like. Then, print both in whatever order you choose."
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
                configurations_app.set_config("max-connections", "100", "network")
                .oracle()
                .depends_on(event1, delay_seconds=2)
            )
            oracle2 = (
                configurations_app.set_config("log-level", "debug", "system")
                .oracle()
                .depends_on(oracle1, delay_seconds=2)
            )
            oracle3 = (
                configurations_app.print_config("max-connections")
                .oracle()
                .depends_on(oracle2, delay_seconds=2)
            )
            oracle4 = (
                configurations_app.print_config("log-level")
                .oracle()
                .depends_on(oracle3, delay_seconds=2)
            )

            # branching for different orders
            oracle5 = (
                configurations_app.print_config("log-level")
                .oracle()
                .depends_on(oracle2, delay_seconds=2)
            )
            oracle6 = (
                configurations_app.print_config("max-connections")
                .oracle()
                .depends_on(oracle5, delay_seconds=2)
            )

            oracle7 = (
                configurations_app.set_config("log-level", "debug", "system")
                .oracle()
                .depends_on(event1, delay_seconds=2)
            )
            oracle8 = (
                configurations_app.set_config("max-connections", "100", "network")
                .oracle()
                .depends_on(oracle7, delay_seconds=2)
            )
            oracle9 = (
                configurations_app.print_config("max-connections")
                .oracle()
                .depends_on(oracle8, delay_seconds=2)
            )
            oracle10 = (
                configurations_app.print_config("log-level")
                .oracle()
                .depends_on(oracle9, delay_seconds=2)
            )

            oracle11 = (
                configurations_app.print_config("log-level")
                .oracle()
                .depends_on(oracle8, delay_seconds=2)
            )
            oracle12 = (
                configurations_app.print_config("max-connections")
                .oracle()
                .depends_on(oracle11, delay_seconds=2)
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
            oracle12,
        ]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    # Run the scenario in oracle mode and validate the agent actions
    run_and_validate(CustomScenario())
