from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.transactions import TransactionsApp
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.types import EventRegisterer


class CustomScenario(COREScenario):
    """
    @TODO: Update this docstring.
    """

    prompt: str | None = (
        "Create two accounts 'E111' and 'F222' in that order, deposit 500 into 'E111' and apply to it 0.1 interest. Then, transfer all of its money to 'F222' and close 'E111'."
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
                transactions_app.create_account(account_id="E111")
                .oracle()
                .depends_on(event1, delay_seconds=2)
            )
            oracle2 = (
                transactions_app.create_account(account_id="F222")
                .oracle()
                .depends_on(oracle1, delay_seconds=2)
            )
            oracle3 = (
                transactions_app.deposit(account_id="E111", amount=500)
                .oracle()
                .depends_on(oracle2, delay_seconds=2)
            )
            oracle4 = (
                transactions_app.apply_interest(account_id="E111", rate=0.1)
                .oracle()
                .depends_on(oracle3, delay_seconds=2)
            )
            oracle5 = (
                transactions_app.transfer(
                    sender_id="E111", receiver_id="F222", amount=550
                )
                .oracle()
                .depends_on(oracle4, delay_seconds=2)
            )
            oracle6 = (
                transactions_app.close_account(account_id="E111")
                .oracle()
                .depends_on(oracle5, delay_seconds=2)
            )

        self.events = [
            event1,
            oracle1,
            oracle2,
            oracle3,
            oracle4,
            oracle5,
            oracle6,
        ]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    # Run the scenario in oracle mode and validate the agent actions
    run_and_validate(CustomScenario())
