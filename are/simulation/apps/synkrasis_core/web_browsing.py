# @TODO: Update copyright for SYNKRASIS-LABS
#
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

import os
from dataclasses import dataclass

from are.simulation.apps.core_app import COREApp
from are.simulation.tool_utils import OperationType, app_tool, data_tool
from are.simulation.types import event_registered
from are.simulation.utils import type_check


@dataclass
class WebBrowsingState:
    """
    State of the web browsing system.
    """

    current_url: str | None
    history: list[str]


initState = WebBrowsingState(
    current_url=None,
    history=[],  # Stores previously visited URLs
)


class WebBrowsingApp(COREApp[WebBrowsingState]):
    """
    A web browsing app demonstrating core app implementation patterns.

    Key Features Demonstrated:
    - Data storage and management
    - Tool method registration with decorators
    - State persistence and loading
    - Type checking and validation
    - Event registration for environment integration

    This app manages web page navigation with basic browsing operations.
    """

    init_state: WebBrowsingState = initState

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def move_to_url(self, file_name: str) -> str:
        """
        Navigates to a given web page by loading its HTML file.

        :param file_name: The name of the HTML file to navigate to.
        :returns: Confirmation message.
        """
        if os.path.exists(file_name):
            if self.state.current_url:
                self.state.history.append(self.state.current_url)
            self.state.current_url = file_name
            return f"Moved to {file_name}."
        return "Page not found."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_page_source(self) -> str:
        """
        Retrieves the HTML source of the current page.

        :returns: The HTML source of the current page, or None if no page is loaded.
        """
        if self.state.current_url:
            with open(self.state.current_url, "r", encoding="utf-8") as file:
                return file.read()
        return "No page loaded."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def find_text_in_page(self, text: str) -> bool:
        """
        Searches for a given text in the current page's HTML source.

        :param text: The text to search for.
        :returns: True if the text is found, False otherwise.
        """
        if self.state.current_url:
            with open(self.state.current_url, "r", encoding="utf-8") as file:
                return text in file.read()
        return False

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_current_url(self) -> str | None:
        """
        Retrieves the currently loaded page's file name.

        :returns: The name of the currently loaded HTML file, or None if no page is loaded.
        """
        return self.state.current_url

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def go_back(self) -> str:
        """
        Navigates back to the previous page if available.

        :returns: Confirmation message.
        """
        if self.state.history:
            self.state.current_url = self.state.history.pop()
            return f"Went back to {self.state.current_url}."
        self.state.current_url = None
        return "No previous page to go back to."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def view_browsing_history(self) -> list[str]:
        """
        Returns the list of previously visited URLs.

        :returns: List of visited URLs.
        """
        return self.state.history
