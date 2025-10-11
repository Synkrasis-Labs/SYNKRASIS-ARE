from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.validation import ValidationApp
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.types import EventRegisterer


class CustomScenario(COREScenario):
    """
    @TODO: Update this docstring.
    """

    prompt: str | None = "Validate the email 'user@example.com'."

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        """Initialize apps and populate with sample data"""

        agui = AgentUserInterface()
        validation_app = ValidationApp()  # already populated with default data

        # Store apps for scenario use
        self.apps = [
            agui,
            validation_app,
        ]

    def build_events_flow(self) -> None:
        """Define the sequence of events that will occur during the scenario"""

        agui = self.get_typed_app(AgentUserInterface)
        validation_app = self.get_typed_app(ValidationApp)

        with EventRegisterer.capture_mode():
            # User event: User requests task creation
            event1 = agui.send_message_to_agent(
                content=self.prompt,
            ).depends_on(None, delay_seconds=2)
            oracle1 = (
                validation_app.validate_email(email="user@example.com")
                .oracle()
                .depends_on(event1, delay_seconds=2)
            )

        self.events = [
            event1,
            oracle1,
        ]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    # Run the scenario in oracle mode and validate the agent actions
    run_and_validate(CustomScenario())
