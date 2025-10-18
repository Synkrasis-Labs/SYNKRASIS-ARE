from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.desktop_manager import DesktopManagerApp
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.types import EventRegisterer


class CustomScenario(COREScenario):
    """
    @TODO: Update this docstring.
    """

    prompt: str | None = (
        "Open 'Music Player', print its possible actions, play a song ('play_song' action), and finally close the application."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        """Initialize apps and populate with sample data"""

        agui = AgentUserInterface()
        desktop_manager_app = DesktopManagerApp()  # already populated with default data

        # Store apps for scenario use
        self.apps = [
            agui,
            desktop_manager_app,
        ]

    def build_events_flow(self) -> None:
        """Define the sequence of events that will occur during the scenario"""

        agui = self.get_typed_app(AgentUserInterface)
        desktop_manager_app = self.get_typed_app(DesktopManagerApp)

        with EventRegisterer.capture_mode():
            # User event: User requests task creation
            event1 = agui.send_message_to_agent(
                content=self.prompt,
            ).depends_on(None, delay_seconds=2)
            oracle1 = (
                desktop_manager_app.open_application(app_name="Music Player")
                .oracle()
                .depends_on(event1, delay_seconds=2)
            )
            oracle2 = (
                desktop_manager_app.print_application_actions(app_name="Music Player")
                .oracle()
                .depends_on(oracle1, delay_seconds=2)
            )
            oracle3 = (
                desktop_manager_app.perform_action(
                    app_name="Music Player", action="play_song"
                )
                .oracle()
                .depends_on(oracle2, delay_seconds=2)
            )
            oracle4 = (
                desktop_manager_app.close_application(app_name="Music Player")
                .oracle()
                .depends_on(oracle3, delay_seconds=2)
            )

        self.events = [
            event1,
            oracle1,
            oracle2,
            oracle3,
            oracle4,
        ]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    # Run the scenario in oracle mode and validate the agent actions
    run_and_validate(CustomScenario())
