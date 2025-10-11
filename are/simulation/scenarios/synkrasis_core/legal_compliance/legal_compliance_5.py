from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.legal_compliance import LegalComplianceApp
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.types import EventRegisterer


class CustomScenario(COREScenario):
    """
    @TODO: Update this docstring.
    """

    prompt: str | None = (
        "Conduct a comprehensive review of privacy policy enforcement and submit required consent requests"
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
                    statement="Personal data shall not be shared with third parties",
                )
                .oracle()
                .depends_on(event1, delay_seconds=2)
            )
            oracle2 = (
                legal_compliance_app.flag_violation(
                    issue="Third-party data sharing detected"
                )
                .oracle()
                .depends_on(oracle1, delay_seconds=2)
            )
            oracle3 = (
                legal_compliance_app.enforce_compliance(
                    doc_name="privacy_policy",
                    issue="Unauthorized data sharing mitigation",
                )
                .oracle()
                .depends_on(oracle2, delay_seconds=2)
            )
            oracle4 = (
                legal_compliance_app.generate_audit_report(doc_name="privacy_policy")
                .oracle()
                .depends_on(oracle2, delay_seconds=2)
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
