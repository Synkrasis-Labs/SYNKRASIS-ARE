from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.communication import CommunicationApp
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.types import EventRegisterer


class CustomScenario(COREScenario):
    """
    @TODO: Update this docstring.
    """

    prompt: str | None = (
        "Send a normal-priority message from 'Charlie' to 'Dana' with the content 'Lunch at noon'. Then print all of Dana's normal-priority messages. Finally, delete Charlie's messages to Dana."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        """Initialize apps and populate with sample data"""

        agui = AgentUserInterface()
        communication_app = CommunicationApp()  # already populated with default data

        # Store apps for scenario use
        self.apps = [
            agui,
            communication_app,
        ]

    def build_events_flow(self) -> None:
        """Define the sequence of events that will occur during the scenario"""

        agui = self.get_typed_app(AgentUserInterface)
        communication_app = self.get_typed_app(CommunicationApp)

        with EventRegisterer.capture_mode():
            # User event: User requests task creation
            event1 = agui.send_message_to_agent(
                content=self.prompt,
            ).depends_on(None, delay_seconds=2)
            oracle1 = (
                communication_app.send_message(
                    sender="Charlie",
                    recipient="Dana",
                    content="Lunch at noon",
                    priority="normal",
                )
                .oracle()
                .depends_on(event1, delay_seconds=2)
            )
            oracle2 = (
                communication_app.print_messages(recipient="Dana", priority="normal")
                .oracle()
                .depends_on(oracle1, delay_seconds=2)
            )
            oracle3 = (
                communication_app.delete_message(sender="Charlie", recipient="Dana")
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
