# @TODO: Update copyright for SYNKRASIS-LABS
#
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from are.simulation.apps.core_app import COREApp
from are.simulation.tool_utils import OperationType, app_tool, data_tool
from are.simulation.types import event_registered
from are.simulation.utils import type_check


@dataclass
class EventsSchedulerState:
    """
    State of the events scheduler system.
    """

    events: dict[str, str] = field(default_factory=dict)


initState = EventsSchedulerState(events={})


class EventsSchedulerApp(COREApp[EventsSchedulerState]):
    """
    An events scheduler app demonstrating core app implementation patterns.

    Key Features Demonstrated:
    - Data storage and management
    - Tool method registration with decorators
    - State persistence and loading
    - Type checking and validation
    - Event registration for environment integration

    This app manages event scheduling with time-based operations.
    """

    init_state: EventsSchedulerState = initState

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def schedule_event(self, event_name: str, event_time: str) -> str:
        """
        Schedules an event at a specified time.

        :param event_name: The name of the event.
        :param event_time: The scheduled time in ISO 8601 format.
        :returns: Confirmation message.
        """
        self.state.events[event_name] = event_time
        return f"Event '{event_name}' scheduled at {event_time}."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def cancel_event(self, event_name: str) -> str:
        """
        Cancels a scheduled event.

        :param event_name: The name of the event to cancel.
        :returns: Confirmation message.
        """
        if event_name in self.state.events:
            del self.state.events[event_name]
            return f"Event '{event_name}' has been canceled."
        return f"Event '{event_name}' not found."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def list_events(self) -> dict[str, str]:
        """
        Lists all scheduled events with their respective times.

        :returns: Dictionary of scheduled events.
        """
        return self.state.events

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def reschedule_event(self, event_name: str, new_time: str) -> str:
        """
        Reschedules an existing event to a new time.

        :param event_name: The name of the event to reschedule.
        :param new_time: The new event time in ISO 8601 format.
        :returns: Confirmation message.
        """
        if event_name in self.state.events:
            self.state.events[event_name] = new_time
            return f"Event '{event_name}' rescheduled to {new_time}."
        return f"Event '{event_name}' not found."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_event_time(self, event_name: str) -> str | None:
        """
        Retrieves the scheduled time of an event.

        :param event_name: The name of the event.
        :returns: The scheduled time of the event or None if not found.
        """
        return self.state.events.get(event_name, None)

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def time_until_event(self, event_name: str) -> str | None:
        """
        Calculates the remaining time until a scheduled event.

        :param event_name: The name of the event.
        :returns: The remaining time as a string, or None if the event is not found.
        """
        if event_name not in self.state.events:
            return None
        event_time = datetime.fromisoformat(self.state.events[event_name])
        time_difference = event_time - datetime.utcnow()
        return (
            str(time_difference)
            if time_difference.total_seconds() > 0
            else "Event time has passed."
        )

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def schedule_recurring_event(self, event_name: str, interval_minutes: int) -> str:
        """
        Schedules a recurring event that repeats at a fixed interval.

        :param event_name: The name of the event.
        :param interval_minutes: Interval time in minutes.
        :returns: Confirmation message.
        """
        event_time = datetime.utcnow() + timedelta(minutes=interval_minutes)
        self.state.events[event_name] = event_time.isoformat()
        return f"Recurring event '{event_name}' scheduled every {interval_minutes} minutes."
