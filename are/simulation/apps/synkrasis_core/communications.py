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
class Message:
    """
    Represents a message in the communication system.
    """

    sender: str
    recipient: str
    content: str
    priority: str
    timestamp: str


@dataclass
class CommunicationsState:
    """
    State of the communications system.
    """

    messages: list[Message] = field(default_factory=list)


initState = CommunicationsState(messages=[])


class CommunicationsApp(COREApp[CommunicationsState]):
    """
    A communications app demonstrating core app implementation patterns.

    Key Features Demonstrated:
    - Data storage and management
    - Tool method registration with decorators
    - State persistence and loading
    - Type checking and validation
    - Event registration for environment integration

    This app manages message communication between users.
    """

    init_state: CommunicationsState = initState

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def send_message(
        self,
        sender: str,
        recipient: str,
        content: str,
        priority: str,
        timestamp: str | None = None,
    ) -> str:
        """
        Sends a message from a sender to a recipient.

        :param sender: The sender's name or identifier.
        :param recipient: The recipient's name or identifier.
        :param content: The message content.
        :param priority: Message priority (default: "normal"). Enum: ["low", "normal", "high"]
        :param timestamp: Optional timestamp of when the message was sent.
        :returns: Confirmation message.
        """
        if timestamp is None:
            timestamp = datetime.utcnow().isoformat()
        message = Message(
            sender=sender,
            recipient=recipient,
            content=content,
            priority=priority,
            timestamp=timestamp,
        )
        self.state.messages.append(message)
        return (
            f"Message sent from '{sender}' to '{recipient}' with priority '{priority}'."
        )

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def print_messages(self, recipient: str, priority: str) -> list[dict[str, str]]:
        """
        Prints messages for a specific recipient, optionally filtering by priority.

        :param recipient: The recipient whose messages should be printed.
        :param priority: Optionally filter messages by priority.  Enum: ["low", "normal", "high"]
        :returns: A list of messages.
        """
        return [
            {
                "sender": msg.sender,
                "recipient": msg.recipient,
                "content": msg.content,
                "priority": msg.priority,
                "timestamp": msg.timestamp,
            }
            for msg in self.state.messages
            if msg.recipient == recipient and msg.priority == priority
        ]

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def delete_message(self, sender: str, recipient: str) -> str:
        """
        Deletes a message based on sender, recipient, and timestamp.

        :param sender: The sender of the message.
        :param recipient: The recipient of the message.
        :returns: Confirmation message.
        """
        self.state.messages = [
            msg
            for msg in self.state.messages
            if not (msg.sender == sender and msg.recipient == recipient)
        ]
        return f"Message from '{sender}' to '{recipient}' has been deleted."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def forward_message(
        self,
        original_sender: str,
        new_recipient: str,
        timestamp: str,
        forwarded_by: str,
    ) -> str:
        """
        Forwards a message to a new recipient.

        :param original_sender: The sender of the original message.
        :param new_recipient: The new recipient of the forwarded message.
        :param timestamp: The timestamp of the original message.
        :param forwarded_by: The user forwarding the message.
        :returns: Confirmation message.
        """
        for msg in self.state.messages:
            if msg.sender == original_sender and msg.timestamp == timestamp:
                new_message = Message(
                    sender=forwarded_by,
                    recipient=new_recipient,
                    content=msg.content,
                    priority=msg.priority,
                    timestamp=msg.timestamp,
                )
                self.state.messages.append(new_message)
                return f"Message from '{original_sender}' forwarded to '{new_recipient}' by '{forwarded_by}'."
        return "Original message not found."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def schedule_message(
        self,
        sender: str,
        recipient: str,
        content: str,
        send_time: str,
        priority: str = "normal",
    ) -> str:
        """
        Schedules a message to be sent at a later time.

        :param sender: The sender's name or identifier.
        :param recipient: The recipient's name or identifier.
        :param content: The message content.
        :param send_time: The scheduled time to send the message in ISO 8601 format.
        :param priority: Message priority (default: "normal").  Enum: ["low", "normal", "high"]
        :returns: Confirmation message.
        """
        message = Message(
            sender=sender,
            recipient=recipient,
            content=content,
            priority=priority,
            timestamp=send_time,
        )
        self.state.messages.append(message)
        return f"Message from '{sender}' to '{recipient}' scheduled for {send_time} with priority '{priority}'."
