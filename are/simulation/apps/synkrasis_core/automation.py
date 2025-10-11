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
class AutomationState:
    """
    State of the automation system.
    """

    lights_on: bool
    thermostat: int
    door_locked: bool
    alarm_on: bool


initState = AutomationState(
    lights_on=False, thermostat=22, door_locked=True, alarm_on=False
)


class AutomationApp(COREApp[AutomationState]):
    """
    An automation app demonstrating core app implementation patterns.

    Key Features Demonstrated:
    - Data storage and management
    - Tool method registration with decorators
    - State persistence and loading
    - Type checking and validation
    - Event registration for environment integration

    This app manages home automation systems including lights, thermostat, door locks, and alarms.
    """

    init_state: AutomationState = initState

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def turn_on_lights(self) -> str:
        """
        Turns on the lights in the system.

        :returns: Confirmation message
        """
        self.state.lights_on = True
        return "Lights turned on."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def turn_off_lights(self) -> str:
        """
        Turns off the lights in the system.

        :returns: Confirmation message
        """
        self.state.lights_on = False
        return "Lights turned off."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def set_thermostat(self, temperature: int) -> str:
        """
        Sets the thermostat to the specified temperature.

        :param temperature: Desired temperature setting.
        :returns: Confirmation message
        """
        self.state.thermostat = temperature
        return f"Thermostat set to {temperature} degrees."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def lock_door(self) -> str:
        """
        Locks the main door.

        :returns: Confirmation message
        """
        self.state.door_locked = True
        return "Door locked."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def unlock_door(self) -> str:
        """
        Unlocks the main door.

        :returns: Confirmation message
        """
        self.state.door_locked = False
        return "Door unlocked."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def activate_alarm(self) -> str:
        """
        Activates the security alarm.

        :returns: Confirmation message
        """
        self.state.alarm_on = True
        return "Alarm activated."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def deactivate_alarm(self) -> str:
        """
        Deactivates the security alarm.

        :returns: Confirmation message
        """
        self.state.alarm_on = False
        return "Alarm deactivated."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def print_system_status(self) -> dict[str, bool | int]:
        """
        Returns the current status of the system.

        :returns: Dictionary with system state information
        """
        return {
            "lights_on": self.state.lights_on,
            "thermostat": self.state.thermostat,
            "door_locked": self.state.door_locked,
            "alarm_on": self.state.alarm_on,
        }
