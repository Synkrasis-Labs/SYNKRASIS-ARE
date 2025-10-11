from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.legal_compliance import LegalComplianceApp
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.types import EventRegisterer


class CustomScenario(COREScenario):
    """
    @TODO: Update this docstring.
    """

    prompt: str | None = (
        "Verify if the statement 'Users must be informed before data collection' adheres to our privacy policy. If it does, approve it as a valid policy statement."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        """Initialize apps and populate with sample data"""

        agui = AgentUserInterface()
        legal_compliance_app = (
            LegalComplianceApp()
        )  # already populated with default data

        # Store apps for scenario use
        self.apps = [
            agui,
            legal_compliance_app,
        ]

    def build_events_flow(self) -> None:
        """Define the sequence of events that will occur during the scenario"""

        agui = self.get_typed_app(AgentUserInterface)
        legal_compliance_app = self.get_typed_app(LegalComplianceApp)

        with EventRegisterer.capture_mode():
            # User event: User requests task creation
            event1 = agui.send_message_to_agent(
                content=self.prompt,
            ).depends_on(None, delay_seconds=2)
            oracle1 = (
                legal_compliance_app.check_compliance(
                    doc_name="privacy_policy",
                    statement="Users must be informed before data collection",
                )
                .oracle()
                .depends_on(event1, delay_seconds=2)
            )
            oracle2 = (
                legal_compliance_app.approve_policy(
                    statement="Users must be informed before data collection"
                )
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
