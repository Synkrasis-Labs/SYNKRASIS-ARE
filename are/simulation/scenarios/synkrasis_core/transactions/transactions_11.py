from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.transactions import TransactionsApp
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.types import EventRegisterer


class CustomScenario(COREScenario):
    """
    @TODO: Update this docstring.
    """

    prompt: str | None = (
        "Create account 'D001', deposit 50, apply 0.1 interest, then charge a maintenance fee of 10."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        """Initialize apps and populate with sample data"""

        agui = AgentUserInterface()
        transactions_app = TransactionsApp()  # already populated with default data

        # Store apps for scenario use
        self.apps = [
            agui,
            transactions_app,
        ]

    def build_events_flow(self) -> None:
        """Define the sequence of events that will occur during the scenario"""

        agui = self.get_typed_app(AgentUserInterface)
        transactions_app = self.get_typed_app(TransactionsApp)

        with EventRegisterer.capture_mode():
            # User event: User requests task creation
            event1 = agui.send_message_to_agent(
                content=self.prompt,
            ).depends_on(None, delay_seconds=2)
            oracle1 = (
                transactions_app.create_account(account_id="D001")
                .oracle()
                .depends_on(event1, delay_seconds=2)
            )
            oracle2 = (
                transactions_app.deposit(account_id="D001", amount=50)
                .oracle()
                .depends_on(oracle1, delay_seconds=2)
            )
            oracle3 = (
                transactions_app.apply_interest(account_id="D001", rate=0.1)
                .oracle()
                .depends_on(oracle2, delay_seconds=2)
            )
            oracle4 = (
                transactions_app.charge_fee(account_id="D001", amount=10)
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
