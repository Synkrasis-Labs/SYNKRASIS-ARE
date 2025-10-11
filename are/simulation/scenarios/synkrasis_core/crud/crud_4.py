from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.crud import CRUDApp
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.types import EventRegisterer


class CustomScenario(COREScenario):
    """
    @TODO: Update this docstring.
    """

    prompt: str | None = (
        "Add a new user named 'Charlie' aged 40 with email 'charlie@email.com'. Then, delete that user. Finally, confirm the deletion by showing all the users."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        """Initialize apps and populate with sample data"""

        agui = AgentUserInterface()
        crud_app = CRUDApp()  # already populated with default data

        # Store apps for scenario use
        self.apps = [
            agui,
            crud_app,
        ]

    def build_events_flow(self) -> None:
        """Define the sequence of events that will occur during the scenario"""

        agui = self.get_typed_app(AgentUserInterface)
        crud_app = self.get_typed_app(CRUDApp)

        with EventRegisterer.capture_mode():
            # User event: User requests task creation
            event1 = agui.send_message_to_agent(
                content=self.prompt,
            ).depends_on(None, delay_seconds=2)
            oracle1 = (
                crud_app.add_user(name="Charlie", age=40, email="charlie@email.com")
                .oracle()
                .depends_on(event1, delay_seconds=2)
            )
            oracle2 = (
                crud_app.delete_user(user_id="Charlie_id")
                .oracle()
                .depends_on(oracle1, delay_seconds=2)
            )
            oracle3 = (
                crud_app.list_users().oracle().depends_on(oracle2, delay_seconds=2)
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
