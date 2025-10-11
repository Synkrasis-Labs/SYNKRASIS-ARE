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
class Account:
    """
    Represents a bank account with balance and transaction history.
    """

    balance: float
    transactions: list[str]


@dataclass
class TransactionsState:
    """
    State of the transactions system.
    """

    accounts: dict[str, Account] = field(default_factory=dict)


initState = TransactionsState(accounts={})


class TransactionsApp(COREApp[TransactionsState]):
    """
    A transactions app demonstrating core app implementation patterns.

    Key Features Demonstrated:
    - Data storage and management
    - Tool method registration with decorators
    - State persistence and loading
    - Type checking and validation
    - Event registration for environment integration

    This app manages bank accounts and financial transactions.
    """

    init_state: TransactionsState = initState

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def create_account(self, account_id: str) -> str:
        """
        Creates a new account with zero balance.

        :param account_id: Unique identifier for the account.
        :returns: Confirmation message.
        """
        if account_id not in self.state.accounts:
            self.state.accounts[account_id] = Account(balance=0.0, transactions=[])
            return f"Account '{account_id}' created with balance 0.0."
        return f"Account '{account_id}' already exists."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def deposit(self, account_id: str, amount: float) -> str:
        """
        Deposits money into an account.

        :param account_id: The account to deposit into.
        :param amount: The amount to deposit.
        :returns: Confirmation message.
        """
        if account_id in self.state.accounts:
            self.state.accounts[account_id].balance += amount
            self.state.accounts[account_id].transactions.append(f"Deposit: {amount}")
            return f"Deposited {amount} into account '{account_id}'."
        return f"Account '{account_id}' not found."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def withdraw(self, account_id: str, amount: float) -> str:
        """
        Withdraws money from an account.

        :param account_id: The account to withdraw from.
        :param amount: The amount to withdraw.
        :returns: Confirmation message.
        """
        if (
            account_id in self.state.accounts
            and self.state.accounts[account_id].balance >= amount
        ):
            self.state.accounts[account_id].balance -= amount
            self.state.accounts[account_id].transactions.append(f"Withdrawal: {amount}")
            return f"Withdrew {amount} from account '{account_id}'."
        return f"Insufficient funds or account '{account_id}' not found."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def check_balance(self, account_id: str) -> float:
        """
        Checks the current balance of an account.

        :param account_id: The account to check.
        :returns: The current balance (0.0 if not found).
        """
        if account_id in self.state.accounts:
            return self.state.accounts[account_id].balance
        return 0.0

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def transfer(self, sender_id: str, receiver_id: str, amount: float) -> str:
        """
        Transfers money from one account to another.

        :param sender_id: The account sending money.
        :param receiver_id: The account receiving money.
        :param amount: The amount to transfer.
        :returns: Confirmation message.
        """
        if (
            sender_id in self.state.accounts
            and receiver_id in self.state.accounts
            and self.state.accounts[sender_id].balance >= amount
        ):
            self.state.accounts[sender_id].balance -= amount
            self.state.accounts[receiver_id].balance += amount
            self.state.accounts[sender_id].transactions.append(
                f"Transfer to {receiver_id}: {amount}"
            )
            self.state.accounts[receiver_id].transactions.append(
                f"Transfer from {sender_id}: {amount}"
            )
            return f"Transferred {amount} from '{sender_id}' to '{receiver_id}'."
        return "Insufficient funds or account(s) not found."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_transaction_history(self, account_id: str) -> list[str]:
        """
        Retrieves the transaction history of an account.

        :param account_id: The account to check.
        :returns: List of transactions (empty list if not found).
        """
        if account_id in self.state.accounts:
            return self.state.accounts[account_id].transactions
        return []

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def apply_interest(self, account_id: str, rate: float) -> str:
        """
        Applies interest to an account balance.

        :param account_id: The account to apply interest to.
        :param rate: Interest rate as a decimal (e.g., 0.05 for 5%).
        :returns: Confirmation message.
        """
        if account_id in self.state.accounts:
            interest = self.state.accounts[account_id].balance * rate
            self.state.accounts[account_id].balance += interest
            self.state.accounts[account_id].transactions.append(
                f"Interest applied: {interest}"
            )
            return f"Applied {rate * 100}% interest to account '{account_id}'."
        return f"Account '{account_id}' not found."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def close_account(self, account_id: str) -> str:
        """
        Closes an account and removes it from the system.

        :param account_id: The account to close.
        :returns: Confirmation message.
        """
        if account_id in self.state.accounts:
            del self.state.accounts[account_id]
            return f"Account '{account_id}' closed."
        return f"Account '{account_id}' not found."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def charge_fee(self, account_id: str, amount: float) -> str:
        """
        Charges a fee to an account.

        :param account_id: The account to charge.
        :param amount: The fee amount.
        :returns: Confirmation message.
        """
        if (
            account_id in self.state.accounts
            and self.state.accounts[account_id].balance >= amount
        ):
            self.state.accounts[account_id].balance -= amount
            self.state.accounts[account_id].transactions.append(
                f"Fee charged: {amount}"
            )
            return f"Charged a fee of {amount} to account '{account_id}'."
        return f"Insufficient funds or account '{account_id}' not found."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def refund(self, account_id: str, amount: float) -> str:
        """
        Issues a refund to an account.

        :param account_id: The account to refund.
        :param amount: The refund amount.
        :returns: Confirmation message.
        """
        if account_id in self.state.accounts:
            self.state.accounts[account_id].balance += amount
            self.state.accounts[account_id].transactions.append(f"Refund: {amount}")
            return f"Refunded {amount} to account '{account_id}'."
        return f"Account '{account_id}' not found."
