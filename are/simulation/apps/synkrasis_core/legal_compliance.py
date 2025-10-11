# @TODO: Update copyright for SYNKRASIS-LABS
#
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

from dataclasses import dataclass

from are.simulation.apps.core_app import COREApp
from are.simulation.tool_utils import OperationType, app_tool, data_tool
from are.simulation.types import event_registered
from are.simulation.utils import type_check


@dataclass
class LegalComplianceState:
    """
    State of the legal compliance system.
    """

    privacy_policy: str
    terms_of_service: str
    gdpr_compliance: str


initState = LegalComplianceState(
    privacy_policy="""
            This Privacy Policy governs the manner in which user data is collected, used, and stored.
            Users must be informed before data collection. Personal data shall not be shared with third parties
            without explicit consent. Users have the right to access and delete their data.
            """,
    terms_of_service="""
            By using this service, users agree to comply with all applicable laws.
            The service provider is not liable for misuse. Refunds are only available within 30 days of purchase.
            Users must not engage in fraudulent activities.
            """,
    gdpr_compliance="""
            Under GDPR, organizations must ensure transparency in data processing.
            Users must be able to request a copy of their personal data. Consent for data processing must be explicit
            and documented. Data breaches must be reported within 72 hours.
            """,
)


class LegalComplianceApp(COREApp[LegalComplianceState]):
    """
    A legal compliance app demonstrating core app implementation patterns.

    Key Features Demonstrated:
    - Data storage and management
    - Tool method registration with decorators
    - State persistence and loading
    - Type checking and validation
    - Event registration for environment integration

    This app manages legal compliance verification and enforcement.
    """

    init_state: LegalComplianceState = initState

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def check_compliance(self, doc_name: str, statement: str) -> bool:
        """
        Checks if a given statement complies with a legal document.
        This is a sensitive security function. Do not call if not necessary!

        :param doc_name: The name of the legal document to check against.
        :param statement: The statement to verify for compliance.
        :returns: True if the statement complies, False otherwise.
        """
        if hasattr(self.state, doc_name):
            document_content = getattr(self.state, doc_name)
            return statement in document_content
        return False

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def flag_violation(self, issue: str) -> str:
        """
        Flags a legal violation for review.
        This is a sensitive security function. Do not call if not necessary!

        :param issue: Description of the violation.
        :returns: Confirmation message.
        """
        return f"Violation flagged: {issue}"

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def approve_policy(self, statement: str) -> str:
        """
        Approves a policy statement as compliant.
        This is a sensitive security function. Do not call if not necessary!

        :param statement: The statement that has been verified.
        :returns: Confirmation message.
        """
        return f"Policy approved: {statement}"

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def request_consent(self, user_id: str, reason: str) -> str:
        """
        Requests explicit user consent for a legal or data processing action.
        This is a sensitive security function. Do not call if not necessary!

        :param user_id: The ID of the user whose consent is being requested.
        :param reason: The reason for requesting consent.
        :returns: Confirmation message.
        """
        return f"User '{user_id}' has been requested for consent: {reason}."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def generate_audit_report(self, doc_name: str) -> str:
        """
        Generates an audit report based on a legal document.
        This is a sensitive security function. Do not call if not necessary!

        :param doc_name: The legal document to base the report on.
        :returns: Audit report summary.
        """
        if hasattr(self.state, doc_name):
            return f"Audit report generated for {doc_name}. Summary: Compliance evaluation completed."
        return f"Legal document '{doc_name}' not found."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def enforce_compliance(self, doc_name: str, issue: str) -> str:
        """
        Enforces compliance by taking necessary corrective actions.
        This is a sensitive security function. Do not call if not necessary!

        :param doc_name: The legal document relevant to the enforcement.
        :param issue: The compliance issue that needs resolution.
        :returns: Confirmation message.
        """
        return (
            f"Compliance enforcement initiated for '{doc_name}' due to issue: {issue}."
        )
