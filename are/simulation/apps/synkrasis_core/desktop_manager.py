# @TODO: Update copyright for SYNKRASIS-LABS
#
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

from dataclasses import dataclass, field

from are.simulation.apps.core_app import COREApp
from are.simulation.tool_utils import OperationType, app_tool, data_tool
from are.simulation.types import event_registered
from are.simulation.utils import type_check


@dataclass
class DesktopManagerState:
    """
    State of the desktop manager system.
    """

    open_applications: list[str] = field(default_factory=list)
    app_history: list[str] = field(default_factory=list)
    action_log: dict[str, list[str]] = field(default_factory=dict)


initState = DesktopManagerState(open_applications=[], app_history=[], action_log={})


class DesktopManagerApp(COREApp[DesktopManagerState]):
    """
    A desktop manager app demonstrating core app implementation patterns.

    Key Features Demonstrated:
    - Data storage and management
    - Tool method registration with decorators
    - State persistence and loading
    - Type checking and validation
    - Event registration for environment integration

    This app manages desktop applications and their action logs.
    """

    init_state: DesktopManagerState = initState

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def open_application(self, app_name: str) -> str:
        """
        Opens an application and adds it to the open applications list.

        :param app_name: The name of the application to open.
        :returns: Confirmation message.
        """
        if app_name not in self.state.open_applications:
            self.state.open_applications.append(app_name)
            self.state.app_history.append(app_name)
            self.state.action_log[app_name] = []
            return f"Opened application '{app_name}'."
        return f"Application '{app_name}' is already open."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def close_application(self, app_name: str) -> str:
        """
        Closes an application if it is currently open.

        :param app_name: The name of the application to close.
        :returns: Confirmation message.
        """
        if app_name in self.state.open_applications:
            self.state.open_applications.remove(app_name)
            return f"Closed application '{app_name}'."
        return f"Application '{app_name}' is not open."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def print_open_applications(self) -> list[str]:
        """
        Prints a list of currently open applications.

        :returns: List of open application names.
        """
        return self.state.open_applications

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def print_application_history(self) -> list[str]:
        """
        Prints the history of all applications that have been opened.

        :returns: List of application names.
        """
        return self.state.app_history

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def perform_action(self, app_name: str, action: str) -> str:
        """
        Logs an action performed in an open application.

        :param app_name: The name of the application where the action is performed.
        :param action: The action to log.
        :returns: Confirmation message.
        """
        if app_name in self.state.open_applications:
            self.state.action_log[app_name].append(action)
            return f"Performed action '{action}' in application '{app_name}'."
        return f"Application '{app_name}' is not open."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def print_application_actions(self, app_name: str) -> list[str]:
        """
        Prints the action log for a specific application.

        :param app_name: The name of the application.
        :returns: List of actions performed in the application.
        """
        return self.state.action_log.get(app_name, [])
