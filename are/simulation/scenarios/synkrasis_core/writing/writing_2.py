from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.writing import WritingApp
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.types import EventRegisterer


class CustomScenario(COREScenario):
    """
    @TODO: Update this docstring.
    """

    prompt: str | None = (
        "Write a sentence about a small dog sleeping under a tree. Use present simple tense for the verb"
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        """Initialize apps and populate with sample data"""

        agui = AgentUserInterface()
        writing_app = WritingApp()  # already populated with default data

        # Store apps for scenario use
        self.apps = [
            agui,
            writing_app,
        ]

    def build_events_flow(self) -> None:
        """Define the sequence of events that will occur during the scenario"""

        agui = self.get_typed_app(AgentUserInterface)
        writing_app = self.get_typed_app(WritingApp)

        with EventRegisterer.capture_mode():
            # User event: User requests task creation
            event1 = agui.send_message_to_agent(
                content=self.prompt,
            ).depends_on(None, delay_seconds=2)
            oracle1 = (
                writing_app.add_article(article="a")
                .oracle()
                .depends_on(event1, delay_seconds=2)
            )
            oracle2 = (
                writing_app.add_adjective(adjective="small")
                .oracle()
                .depends_on(oracle1, delay_seconds=2)
            )
            oracle3 = (
                writing_app.add_noun(noun="dog")
                .oracle()
                .depends_on(oracle2, delay_seconds=2)
            )
            oracle4 = (
                writing_app.add_verb(verb="sleeps")
                .oracle()
                .depends_on(oracle3, delay_seconds=2)
            )
            oracle5 = (
                writing_app.add_preposition(preposition="under")
                .oracle()
                .depends_on(oracle4, delay_seconds=2)
            )
            oracle6 = (
                writing_app.add_article(article="a")
                .oracle()
                .depends_on(oracle5, delay_seconds=2)
            )
            oracle7 = (
                writing_app.add_noun(noun="tree")
                .oracle()
                .depends_on(oracle6, delay_seconds=2)
            )
            oracle8 = (
                writing_app.complete_sentence()
                .oracle()
                .depends_on(oracle7, delay_seconds=2)
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
        ]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    # Run the scenario in oracle mode and validate the agent actions
    run_and_validate(CustomScenario())
