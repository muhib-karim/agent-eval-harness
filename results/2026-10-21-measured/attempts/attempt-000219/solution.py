import threading
from typing import List, Tuple
from collections import defaultdict

class InsufficientFunds(ValueError):
    pass

class Ledger:
    def __init__(self):
        self._lock = threading.RLock()
        self._accounts = {}  # account_id -> balance
        self._history = defaultdict(list)  # account_id -> list of (kind, amount)

    def open(self, account: str, balance: int = 0) -> None:
        """Create an account with an initial balance."""
        # Validate arguments
        if not isinstance(account, str) or not account:
            raise ValueError("Account id must be a non-empty string")
        if not isinstance(balance, int) or isinstance(balance, bool):
            raise ValueError("Balance must be an int (not bool)")
        if balance < 0:
            raise ValueError("Balance must be non-negative")

        with self._lock:
            if account in self._accounts:
                raise ValueError(f"Account {account} already exists")

            self._accounts[account] = balance
            self._history[account].append(("open", balance))

    def balance(self, account: str) -> int:
        """Get the current balance of an account."""
        with self._lock:
            if account not in self._accounts:
                raise KeyError(f"Account {account} not found")
            return self._accounts[account]

    def deposit(self, account: str, amount: int) -> None:
        """Deposit money into an account."""
        # Validate amount
        if not isinstance(amount, int) or isinstance(amount, bool):
            raise ValueError("Amount must be an int (not bool)")
        if amount <= 0:
            raise ValueError("Amount must be positive")

        with self._lock:
            if account not in self._accounts:
                raise KeyError(f"Account {account} not found")

            self._accounts[account] += amount
            self._history[account].append(("deposit", amount))

    def withdraw(self, account: str, amount: int) -> None:
        """Withdraw money from an account."""
        # Validate amount
        if not isinstance(amount, int) or isinstance(amount, bool):
            raise ValueError("Amount must be an int (not bool)")
        if amount <= 0:
            raise ValueError("Amount must be positive")

        with self._lock:
            if account not in self._accounts:
                raise KeyError(f"Account {account} not found")

            if self._accounts[account] < amount:
                raise InsufficientFunds(f"Insufficient funds in {account}")

            self._accounts[account] -= amount
            self._history[account].append(("withdraw", amount))

    def transfer(self, src: str, dst: str, amount: int) -> None:
        """Transfer money from src to dst atomically."""
        # Validate src != dst
        if src == dst:
            raise ValueError("Source and destination must be different")

        # Validate amount
        if not isinstance(amount, int) or isinstance(amount, bool):
            raise ValueError("Amount must be an int (not bool)")
        if amount <= 0:
            raise ValueError("Amount must be positive")

        # To prevent deadlock, always acquire locks in a consistent order
        # based on account names (alphabetically)
        accounts_ordered = sorted([src, dst])
        first_account = accounts_ordered[0]
        second_account = accounts_ordered[1]

        with self._lock:
            # Check both accounts exist
            if src not in self._accounts:
                raise KeyError(f"Account {src} not found")
            if dst not in self._accounts:
                raise KeyError(f"Account {dst} not found")

            # Check sufficient funds
            if self._accounts[src] < amount:
                raise InsufficientFunds(f"Insufficient funds in {src}")

            # Perform transfer
            self._accounts[src] -= amount
            self._accounts[dst] += amount
            self._history[src].append(("transfer_out", amount))
            self._history[dst].append(("transfer_in", amount))

    def total(self) -> int:
        """Get the total of all balances as a consistent snapshot."""
        with self._lock:
            return sum(self._accounts.values())

    def history(self, account: str) -> List[Tuple[str, int]]:
        """Get the history of operations for an account."""
        with self._lock:
            if account not in self._accounts:
                raise KeyError(f"Account {account} not found")
            # Return a copy of the history
            return list(self._history[account])
