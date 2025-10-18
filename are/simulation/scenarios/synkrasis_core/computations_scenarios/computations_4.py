from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.computations import ComputationsApp
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.types import EventRegisterer


class CustomScenario(COREScenario):
    """
    @TODO: Update this docstring.
    """

    prompt: str | None = (
        "Subtract 4 from 25 and divide the result by 3. Then, calculate the average of this quotient and the product of 4 and 5."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        """Initialize apps and populate with sample data"""

        agui = AgentUserInterface()
        computations_app = ComputationsApp()  # already populated with default data

        # Store apps for scenario use
        self.apps = [
            agui,
            computations_app,
        ]

    def build_events_flow(self) -> None:
        """Define the sequence of events that will occur during the scenario"""

        agui = self.get_typed_app(AgentUserInterface)
        computations_app = self.get_typed_app(ComputationsApp)

        with EventRegisterer.capture_mode():
            # User event: User requests task creation
            event1 = agui.send_message_to_agent(
                content=self.prompt,
            ).depends_on(None, delay_seconds=2)
            oracle1 = (
                computations_app.subtract_numbers(a=25, b=4)
                .oracle()
                .depends_on(event1, delay_seconds=2)
            )
            oracle2 = (
                computations_app.divide_numbers(a=21, b=3)
                .oracle()
                .depends_on(oracle1, delay_seconds=2)
            )
            oracle3 = (
                computations_app.multiply_numbers(a=4, b=5)
                .oracle()
                .depends_on(oracle2, delay_seconds=2)
            )
            oracle4 = (
                computations_app.calculate_average(numbers=[7, 20])
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
