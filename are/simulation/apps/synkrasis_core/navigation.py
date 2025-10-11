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


def is_within_bounds(position: tuple[int, int], grid_size: tuple[int, int]) -> bool:
    """
    Checks if a given position is within the grid bounds.

    :param position: The (x, y) position to check.
    :param grid_size: The (width, height) of the grid.
    :returns: True if within bounds, False otherwise.
    """
    grid_width, grid_height = grid_size
    x, y = position
    return 0 <= x < grid_width and 0 <= y < grid_height


@dataclass
class NavigationState:
    """
    State of the navigation system.
    """

    player_position: tuple[int, int]
    grid_size: tuple[int, int]


initState = NavigationState(player_position=(0, 0), grid_size=(5, 5))


class NavigationApp(COREApp[NavigationState]):
    """
    A navigation app demonstrating core app implementation patterns.

    Key Features Demonstrated:
    - Data storage and management
    - Tool method registration with decorators
    - State persistence and loading
    - Type checking and validation
    - Event registration for environment integration

    This app manages player movement on a grid-based navigation system.
    """

    init_state: NavigationState = initState

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def move_up(self, steps: int = 1) -> str:
        """
        Moves the player up by a specified number of steps.

        :param steps: The number of steps to move (default: 1).
        :returns: Confirmation message.
        """
        x, y = self.state.player_position
        new_position = (x, y - steps)
        if is_within_bounds(new_position, self.state.grid_size):
            self.state.player_position = new_position
            return f"Moved up to {new_position}."
        return "Move out of bounds."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def move_down(self, steps: int = 1) -> str:
        """
        Moves the player down by a specified number of steps.

        :param steps: The number of steps to move (default: 1).
        :returns: Confirmation message.
        """
        x, y = self.state.player_position
        new_position = (x, y + steps)
        if is_within_bounds(new_position, self.state.grid_size):
            self.state.player_position = new_position
            return f"Moved down to {new_position}."
        return "Move out of bounds."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def move_left(self, steps: int = 1) -> str:
        """
        Moves the player left by a specified number of steps.

        :param steps: The number of steps to move (default: 1).
        :returns: Confirmation message.
        """
        x, y = self.state.player_position
        new_position = (x - steps, y)
        if is_within_bounds(new_position, self.state.grid_size):
            self.state.player_position = new_position
            return f"Moved left to {new_position}."
        return "Move out of bounds."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def move_right(self, steps: int = 1) -> str:
        """
        Moves the player right by a specified number of steps.

        :param steps: The number of steps to move (default: 1).
        :returns: Confirmation message.
        """
        x, y = self.state.player_position
        new_position = (x + steps, y)
        if is_within_bounds(new_position, self.state.grid_size):
            self.state.player_position = new_position
            return f"Moved right to {new_position}."
        return "Move out of bounds."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_player_position(self) -> tuple[int, int]:
        """
        Retrieves the current position of the player.

        :returns: The (x, y) coordinates of the player.
        """
        return self.state.player_position

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def reset_position(self) -> str:
        """
        Resets the player to the starting position.

        :returns: Confirmation message.
        """
        self.state.player_position = (0, 0)
        return "Player position reset to (0, 0)."
