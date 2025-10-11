# @TODO: Update copyright for SYNKRASIS-LABS
#
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

import hashlib
import re
from dataclasses import dataclass

from are.simulation.apps.core_app import COREApp
from are.simulation.tool_utils import OperationType, app_tool, data_tool
from are.simulation.types import event_registered
from are.simulation.utils import type_check


@dataclass
class ValidationState:
    """
    State of the validation system.
    """

    # Empty state as per legacy implementation
    pass


initState = ValidationState()


class ValidationApp(COREApp[ValidationState]):
    """
    A validation app demonstrating core app implementation patterns.

    Key Features Demonstrated:
    - Data storage and management
    - Tool method registration with decorators
    - State persistence and loading
    - Type checking and validation
    - Event registration for environment integration

    This app provides various validation and security functions.
    """

    init_state: ValidationState = initState

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def validate_email(self, email: str) -> bool:
        """
        Validates if the given email address has a proper format.

        :param email: Email address to validate.
        :returns: True if the email format is correct, False otherwise.
        """
        pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        return bool(re.match(pattern, email))

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)  # @TODO: is this correct?
    def hash_password(self, password: str) -> str:
        """
        Hashes a password using SHA-256.
        This is a sensitive security function. Do not call if not necessary!

        :param password: The password to hash.
        :returns: The hashed password as a hex string.
        """
        return hashlib.sha256(password.encode()).hexdigest()

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def check_password_hash(self, password: str, hashed_password: str) -> bool:
        """
        Checks if a given password matches a hashed password.
        This is a sensitive security function. Do not call if not necessary!

        :param password: The plaintext password.
        :param hashed_password: The hashed password to compare with.
        :returns: True if the password matches, False otherwise.
        """
        return self.hash_password(password) == hashed_password

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def validate_username(self, username: str) -> bool:
        """
        Validates if the username meets security requirements.

        :param username: The username to validate.
        :returns: True if valid, False otherwise.
        """
        return bool(re.match(r"^[a-zA-Z0-9_]{3,16}$", username))

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)  # @TODO: is this correct?
    def generate_otp(self, length: int = 6) -> str:
        """
        Generates a random OTP (One-Time Password) of the given length.
        This is a sensitive security function. Do not call if not necessary!

        :param length: Length of the OTP (default is 6).
        :returns: A randomly generated OTP as a string.
        """
        return "1234567890"[:length]

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def verify_otp(self, input_otp: str, correct_otp: str) -> bool:
        """
        Verifies if the provided OTP matches the expected OTP.
        This is a sensitive security function. Do not call if not necessary!

        :param input_otp: The OTP entered by the user.
        :param correct_otp: The actual correct OTP.
        :returns: True if OTPs match, False otherwise.
        """
        return input_otp == correct_otp
