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
class ComputationsState:
    """
    State of the computations system.
    """

    calculations: list[str] = field(default_factory=list)


initState = ComputationsState(calculations=[])


class ComputationsApp(COREApp[ComputationsState]):
    """
    A computations app demonstrating core app implementation patterns.

    Key Features Demonstrated:
    - Data storage and management
    - Tool method registration with decorators
    - State persistence and loading
    - Type checking and validation
    - Event registration for environment integration

    This app manages mathematical computations and their history.
    """

    init_state: ComputationsState = initState

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def add_numbers(self, a: int, b: int) -> int:
        """
        Adds two integers and returns the result.

        :param a: The first integer.
        :param b: The second integer.
        :returns: Sum of a and b.
        """
        result = a + b
        self.state.calculations.append(f"{a} + {b} = {result}")
        return result

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def subtract_numbers(self, a: int, b: int) -> int:
        """
        Subtracts the second integer from the first and returns the result.

        :param a: The first integer.
        :param b: The second integer.
        :returns: Difference of a and b.
        """
        result = a - b
        self.state.calculations.append(f"{a} - {b} = {result}")
        return result

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def multiply_numbers(self, a: int, b: int) -> int:
        """
        Multiplies two integers and returns the product.

        :param a: The first integer.
        :param b: The second integer.
        :returns: Product of a and b.
        """
        result = a * b
        self.state.calculations.append(f"{a} * {b} = {result}")
        return result

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def divide_numbers(self, a: int, b: int) -> float | None:
        """
        Divides the first integer by the second and returns the result.

        :param a: The numerator.
        :param b: The denominator. Must not be zero.
        :returns: Quotient of a and b, or None if division by zero.
        """
        if b == 0:
            self.state.calculations.append(f"{a} / {b} = None")
            return None
        result = a / b
        self.state.calculations.append(f"{a} / {b} = {result}")
        return result

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def power(self, base: int, exponent: int) -> int:
        """
        Raises a base number to a given exponent and returns the result.

        :param base: The base number.
        :param exponent: The exponent to raise the base to.
        :returns: base raised to the power of exponent.
        """
        result = base**exponent
        self.state.calculations.append(f"{base} ^ {exponent} = {result}")
        return result

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def calculate_average(self, numbers: list[int]) -> float:
        """
        Calculates the average of a list of integers.

        :param numbers: A list of integers.
        :returns: The average value.
        """
        if not numbers:
            result = 0.0
            self.state.calculations.append(f"Average of {numbers} = {result}")
            return result
        result = sum(numbers) / len(numbers)
        self.state.calculations.append(f"Average of {numbers} = {result}")
        return result
