from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.events_scheduler import EventsSchedulerApp
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.types import EventRegisterer


class CustomScenario(COREScenario):
    """
    @TODO: Update this docstring.
    """

    prompt: str | None = (
        "Schedule 'Project Review' at '2025-02-11T15:00:00', list all events, then check the time until that event."
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
                events_scheduler_app.schedule_event(
                    event_name="Project Review", event_time="2025-02-11T15:00:00"
                )
                .oracle()
                .depends_on(event1, delay_seconds=2)
            )
            oracle2 = (
                events_scheduler_app.list_events()
                .oracle()
                .depends_on(oracle1, delay_seconds=2)
            )
            oracle3 = (
                events_scheduler_app.time_until_event(event_name="Project Review")
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
