from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.web_browsing import WebBrowsingApp
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.types import EventRegisterer


class CustomScenario(COREScenario):
    """
    @TODO: Update this docstring.
    """

    prompt: str | None = (
        "Retrieve the current URL before and after navigating to 'page3.html'."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        """Initialize apps and populate with sample data"""

        agui = AgentUserInterface()
        web_browsing_app = WebBrowsingApp()  # already populated with default data

        # Store apps for scenario use
        self.apps = [
            agui,
            web_browsing_app,
        ]

    def build_events_flow(self) -> None:
        """Define the sequence of events that will occur during the scenario"""

        agui = self.get_typed_app(AgentUserInterface)
        web_browsing_app = self.get_typed_app(WebBrowsingApp)

        with EventRegisterer.capture_mode():
            # User event: User requests task creation
            event1 = agui.send_message_to_agent(
                content=self.prompt,
            ).depends_on(None, delay_seconds=2)
            oracle1 = (
                web_browsing_app.get_current_url()
                .oracle()
                .depends_on(event1, delay_seconds=2)
            )
            oracle2 = (
                web_browsing_app.move_to_url(file_name="page3.html")
                .oracle()
                .depends_on(oracle1, delay_seconds=2)
            )
            oracle3 = (
                web_browsing_app.get_current_url()
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
