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
class ConfigItem:
    """
    Represents a configuration item.
    """

    value: str
    category: str
    timestamp: str


@dataclass
class ConfigurationsState:
    """
    State of the configurations system.
    """

    configs: dict[str, ConfigItem] = field(default_factory=dict)


initState = ConfigurationsState(configs={})


class ConfigurationsApp(COREApp[ConfigurationsState]):
    """
    A configurations app demonstrating core app implementation patterns.

    Key Features Demonstrated:
    - Data storage and management
    - Tool method registration with decorators
    - State persistence and loading
    - Type checking and validation
    - Event registration for environment integration

    This app manages configuration settings with categories and timestamps.
    """

    init_state: ConfigurationsState = initState

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def set_config(
        self,
        key: str,
        value: str,
        category: str = "general",
        timestamp: str | None = None,
    ) -> str:
        """
        Sets a configuration value in the database.

        :param key: The key for the configuration setting.
        :param value: The value to store.
        :param category: The category of the setting (default is 'general').
        :param timestamp: Optional timestamp for when the setting was changed.
        :returns: Confirmation message.
        """
        if timestamp is None:
            timestamp = datetime.utcnow().isoformat()
        self.state.configs[key] = ConfigItem(
            value=value, category=category, timestamp=timestamp
        )
        return f"Configuration '{key}' set to '{value}' in category '{category}'."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def print_config(self, key: str) -> dict[str, str] | None:
        """
        Print a configuration value from the database.

        :param key: The key of the configuration to retrieve.
        :returns: The configuration data if found, otherwise None.
        """
        config_item = self.state.configs.get(key, None)
        if config_item is None:
            return None
        return {
            "value": config_item.value,
            "category": config_item.category,
            "timestamp": config_item.timestamp,
        }

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def update_config(
        self,
        key: str,
        new_value: str,
        category: str | None = None,
        timestamp: str | None = None,
    ) -> str:
        """
        Updates an existing configuration setting.

        :param key: The key for the configuration setting.
        :param new_value: The new value to update.
        :param category: Optionally change the category.
        :param timestamp: Optional timestamp for when the update occurs.
        :returns: Confirmation message.
        """
        if key not in self.state.configs:
            return f"Configuration '{key}' not found."
        if timestamp is None:
            timestamp = datetime.utcnow().isoformat()

        config_item = self.state.configs[key]
        config_item.value = new_value
        config_item.timestamp = timestamp
        if category is not None:
            config_item.category = category

        return f"Configuration '{key}' updated to '{new_value}' in category '{config_item.category}'."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def delete_config(self, key: str) -> str:
        """
        Deletes a configuration setting from the database.

        :param key: The key of the configuration to delete.
        :returns: Confirmation message.
        """
        if key in self.state.configs:
            del self.state.configs[key]
            return f"Configuration '{key}' has been deleted."
        return f"Configuration '{key}' not found."
