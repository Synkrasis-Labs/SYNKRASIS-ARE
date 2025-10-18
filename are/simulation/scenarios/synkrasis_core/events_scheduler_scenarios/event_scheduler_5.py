from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.events_scheduler import EventsSchedulerApp
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.types import EventRegisterer


class CustomScenario(COREScenario):
    """
    @TODO: Update this docstring.
    """

    prompt: str | None = (
        "Schedule a recurring stand-up meeting every 30 minutes and retrieve its scheduled time."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        """Initialize apps and populate with sample data"""

        agui = AgentUserInterface()
        events_scheduler_app = (
            EventsSchedulerApp()
        )  # already populated with default data

        # Store apps for scenario use
        self.apps = [
            agui,
            events_scheduler_app,
        ]

    def build_events_flow(self) -> None:
        """Define the sequence of events that will occur during the scenario"""

        agui = self.get_typed_app(AgentUserInterface)
        events_scheduler_app = self.get_typed_app(EventsSchedulerApp)

        with EventRegisterer.capture_mode():
            # User event: User requests task creation
            event1 = agui.send_message_to_agent(
                content=self.prompt,
            ).depends_on(None, delay_seconds=2)
            oracle1 = (
                events_scheduler_app.schedule_recurring_event(
                    event_name="Stand-up Meeting", interval_minutes=30
                )
                .oracle()
                .depends_on(event1, delay_seconds=2)
            )
            oracle2 = (
                events_scheduler_app.get_event_time(event_name="Stand-up Meeting")
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
