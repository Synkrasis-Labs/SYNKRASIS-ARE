from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.file_management import FileManagementApp
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.types import EventRegisterer


class CustomScenario(COREScenario):
    """
    @TODO: Update this docstring.
    """

    prompt: str | None = (
        "Copy 'meeting_notes.txt' to 'notes.txt' and check the latter's size."
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
                file_management_app.copy_file(
                    source="meeting_notes.txt", destination="notes.txt"
                )
                .oracle()
                .depends_on(event1, delay_seconds=2)
            )
            oracle2 = (
                file_management_app.get_file_size(filename="notes.txt")
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
