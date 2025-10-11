# @TODO: Update copyright for SYNKRASIS-LABS
#
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

from dataclasses import dataclass, field
from datetime import datetime

from are.simulation.apps.core_app import COREApp
from are.simulation.tool_utils import OperationType, app_tool, data_tool
from are.simulation.types import event_registered
from are.simulation.utils import type_check


@dataclass
class User:
    """
    Represents a user in the database.
    """

    id: str
    name: str
    age: int
    email: str | None


@dataclass
class CRUDState:
    """
    State of the CRUD system.
    """

    users: dict[str, User] = field(default_factory=dict)


initState = CRUDState(users={})


class CRUDApp(COREApp[CRUDState]):
    """
    A CRUD app demonstrating core app implementation patterns.

    Key Features Demonstrated:
    - Data storage and management
    - Tool method registration with decorators
    - State persistence and loading
    - Type checking and validation
    - Event registration for environment integration

    This app manages user data with basic CRUD operations.
    """

    init_state: CRUDState = initState

    def _generate_timestamp(self) -> str:
        """Generates the current timestamp in ISO 8601 format."""
        return datetime.utcnow().isoformat() + "Z"

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def add_user(self, name: str, age: int, email: str | None = None) -> str:
        """
        Adds a new user to the database and returns the user ID.

        :param name: The name of the user to be added.
        :param age: The age of the user to be added.
        :param email: The email of the user to be added.
        :returns: user ID
        """
        user_id = f"{name}_id"
        new_user = User(id=user_id, name=name, age=age, email=email)
        self.state.users[user_id] = new_user
        return user_id

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def update_user_email(self, user_id: str, email: str) -> bool:
        """
        Updates a user's email.

        :param user_id: The user ID of the user to be updated.
        :param email: The updated email of the user.
        :returns: True if the user was found and updated, False otherwise
        """
        if user_id not in self.state.users:
            return False
        user = self.state.users[user_id]
        user.email = email
        return True

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def delete_user(self, user_id: str) -> bool:
        """
        Deletes a user from the database by user ID.

        :param user_id: The user ID of the user to be deleted.
        :returns: True if the user was found and deleted, False otherwise
        """
        if user_id in self.state.users:
            del self.state.users[user_id]
            return True
        return False

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def list_users(self) -> list[dict]:
        """
        Returns a list of users, optionally filtered by specific criteria.
        :returns: list of users
        """
        return [
            {"id": user.id, "name": user.name, "age": user.age, "email": user.email}
            for user in self.state.users.values()
        ]

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def verify_user_field(self, user_id: str, field: str, expected_value: str) -> bool:
        """
        Verifies if a specific field in a user record matches the expected value.

        :param user_id: The user ID of the user to be verified.
        :param field: field to check
        :param expected_value: expected value in string form
        :returns: True if the field matches the expected value, False otherwise
        """
        user = self.state.users.get(user_id, None)
        if not user:
            return False
        if field == "age":
            expected_int_value = int(expected_value)
            return getattr(user, field, None) == expected_int_value
        return getattr(user, field, None) == expected_value
