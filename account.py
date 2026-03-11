from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


DATE_FMT = "%Y-%m-%d"


@dataclass
class Transaction:
    transaction_type: str
    amount: float
    date: datetime
    sequence: int


class Account:
    def __init__(
        self,
        account_number: str,
        owner: str,
        initial_balance: float = 0.0,
        interest_rate: float = 0.0,
        opening_date: Optional[str] = None,
    ) -> None:
        self.account_number = str(account_number)
        self.owner = owner
        self.balance = float(initial_balance)
        self.interest_rate = float(interest_rate) / 100
        opened = datetime.strptime(opening_date, DATE_FMT) if opening_date else datetime.now()
        self.transactions: List[Transaction] = [
            Transaction("Initial balance", float(initial_balance), opened, 0)
        ]
        self.locked = False
        self.transaction_counter = 1

    def add_transaction(self, transaction_type: str, amount: float, transaction_date: datetime) -> None:
        self.transactions.append(
            Transaction(transaction_type, float(amount), transaction_date, self.transaction_counter)
        )
        self.transaction_counter += 1

    def deposit(self, amount: float, transaction_date: Optional[str] = None) -> str:
        if self.locked:
            return "Account is locked."
        if amount <= 0:
            return "Invalid amount."
        date = datetime.strptime(transaction_date, DATE_FMT) if transaction_date else datetime.now()
        self.balance += amount
        self.add_transaction("Deposit", amount, date)
        return f"Deposited {amount:.2f}. New balance: {self.balance:.2f}."

    def withdraw(self, amount: float, transaction_date: Optional[str] = None) -> str:
        if self.locked:
            return "Account is locked."
        if amount <= 0 or amount > self.balance:
            return "Invalid amount."
        date = datetime.strptime(transaction_date, DATE_FMT) if transaction_date else datetime.now()
        self.balance -= amount
        self.add_transaction("Withdrawal", amount, date)
        return f"Withdrew {amount:.2f}. New balance: {self.balance:.2f}."

    def transfer(self, target_account: "Account", amount: float, transaction_date: Optional[str] = None) -> str:
        if self.locked:
            return "Account is locked."
        if amount <= 0 or amount > self.balance:
            return "Invalid amount."
        date = datetime.strptime(transaction_date, DATE_FMT) if transaction_date else datetime.now()
        self.balance -= amount
        self.add_transaction("Transfer out", amount, date)
        target_account.balance += amount
        target_account.add_transaction("Transfer in", amount, date)
        return (
            f"Transferred {amount:.2f} to {target_account.account_number}. "
            f"New balance: {self.balance:.2f}."
        )

    def lock_account(self) -> str:
        self.locked = True
        return "Account locked."

    def unlock_account(self) -> str:
        self.locked = False
        return "Account unlocked."

    def _balance_effect(self, transaction_type: str, amount: float) -> float:
        if transaction_type in {"Withdrawal", "Transfer out"}:
            return -amount
        if transaction_type in {"Deposit", "Transfer in"}:
            return amount
        return 0.0

    def calculate_interest(self, as_of: Optional[str] = None) -> Tuple[float, List[dict]]:
        if self.locked:
            return 0.0, []

        sorted_transactions = sorted(self.transactions, key=lambda t: (t.date, t.sequence))
        daily_rate = self.interest_rate / 365
        total_interest = 0.0
        interest_details: List[dict] = []

        rolling_balance = sorted_transactions[0].amount
        last_date = sorted_transactions[0].date

        for tx in sorted_transactions[1:]:
            days = (tx.date - last_date).days
            period_interest = rolling_balance * daily_rate * days
            total_interest += period_interest
            interest_details.append(
                {
                    "account": self.account_number,
                    "interest_rate": self.interest_rate * 100,
                    "date": tx.date.strftime(DATE_FMT),
                    "balance": round(rolling_balance, 2),
                    "interest": round(period_interest, 6),
                }
            )
            rolling_balance += self._balance_effect(tx.transaction_type, tx.amount)
            last_date = tx.date

        end_date = datetime.strptime(as_of, DATE_FMT) if as_of else datetime.now()
        days = (end_date - last_date).days
        period_interest = rolling_balance * daily_rate * max(days, 0)
        total_interest += period_interest
        interest_details.append(
            {
                "account": self.account_number,
                "interest_rate": self.interest_rate * 100,
                "date": end_date.strftime(DATE_FMT),
                "balance": round(rolling_balance, 2),
                "interest": round(period_interest, 6),
            }
        )

        return total_interest, interest_details

    def print_transactions(self) -> None:
        print(
            f"\nAccount {self.account_number} ({self.owner})\n"
            f"{'Type':<15} {'Amount':<10} {'Date':<12} {'Balance':<10}"
        )
        print("-" * 55)

        running_balance = self.transactions[0].amount
        for tx in sorted(self.transactions, key=lambda t: (t.date, t.sequence)):
            if tx.transaction_type != "Initial balance":
                running_balance += self._balance_effect(tx.transaction_type, tx.amount)
            print(
                f"{tx.transaction_type:<15} {tx.amount:<10.2f} "
                f"{tx.date.strftime(DATE_FMT):<12} {running_balance:<10.2f}"
            )


class AccountBook:
    def __init__(self) -> None:
        self.accounts: Dict[str, Account] = {}

    def add_account(self, new_account: Account) -> None:
        self.accounts[new_account.account_number] = new_account

    def get_account(self, account_number: str) -> Account:
        key = str(account_number)
        if key not in self.accounts:
            raise KeyError(f"Account {account_number} does not exist.")
        return self.accounts[key]

    def apply_operation(self, operation: dict) -> str:
        op_type = operation["type"].lower()
        amount = float(operation["amount"])
        date = operation.get("date")

        if op_type == "deposit":
            source_account = self.get_account(operation["account"])
            return source_account.deposit(amount, date)
        if op_type == "withdraw":
            source_account = self.get_account(operation["account"])
            return source_account.withdraw(amount, date)
        if op_type == "transfer":
            source = self.get_account(operation["from_account"])
            target = self.get_account(operation["to_account"])
            return source.transfer(target, amount, date)

        raise ValueError(f"Unsupported operation type: {op_type}")

    @classmethod
    def from_json(cls, data_path: Path) -> "AccountBook":
        payload = json.loads(data_path.read_text(encoding="utf-8"))
        book = cls()

        for item in payload.get("accounts", []):
            book.add_account(
                Account(
                    account_number=str(item["account_number"]),
                    owner=item["owner"],
                    initial_balance=float(item.get("initial_balance", 0)),
                    interest_rate=float(item.get("interest_rate", 0)),
                    opening_date=item.get("opening_date"),
                )
            )

        for operation in payload.get("operations", []):
            result = book.apply_operation(operation)
            print(result)

        return book


if __name__ == "__main__":
    data_file = Path(__file__).with_name("accounts_data.json")
    account_book = AccountBook.from_json(data_file)

    for one_account in account_book.accounts.values():
        one_account.print_transactions()
        account_interest, _ = one_account.calculate_interest()
        print(f"Estimated interest: {account_interest:.6f}")
