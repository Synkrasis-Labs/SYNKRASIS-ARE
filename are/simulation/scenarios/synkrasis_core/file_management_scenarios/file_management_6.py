from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.file_management import FileManagementApp
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.types import EventRegisterer


class CustomScenario(COREScenario):
    """
    @TODO: Update this docstring.
    """

    prompt: str | None = (
        "Search for the word 'agenda' in 'meeting_notes.txt'. If it's not found, append it."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        """Initialize apps and populate with sample data"""

        agui = AgentUserInterface()
        file_management_app = FileManagementApp()  # already populated with default data

        # Store apps for scenario use
        self.apps = [
            agui,
            file_management_app,
        ]

    def build_events_flow(self) -> None:
        """Define the sequence of events that will occur during the scenario"""

        agui = self.get_typed_app(AgentUserInterface)
        file_management_app = self.get_typed_app(FileManagementApp)

        with EventRegisterer.capture_mode():
            # User event: User requests task creation
            event1 = agui.send_message_to_agent(
                content=self.prompt,
            ).depends_on(None, delay_seconds=2)
            oracle1 = (
                file_management_app.search_in_file(
                    filename="meeting_notes.txt", keyword="agenda"
                )
                .oracle()
                .depends_on(event1, delay_seconds=2)
            )
            oracle2 = (
                file_management_app.append_to_file(
                    filename="meeting_notes.txt", content="agenda"
                )
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
