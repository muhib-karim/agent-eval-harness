"""
solution.py

A thread-safe in-memory ledger implementation using the Python standard library.

Design notes:
- A single re-entrant lock (threading.RLock) protects all mutable state
  (balances and histories). This makes every public operation atomic with
  respect to every other public operation, including transfer() (so a
  transfer is never observed "half-done" by total() or balance()), and it
  trivially prevents deadlocks for transfers in opposite directions between
  the same two accounts, since only one transfer (or any other ledger
  operation) can proceed at a time.
- Validation happens before any mutation, and for transfer() all checks are
  done before either balance is touched, so on any error nothing changes.
"""

import threading


class InsufficientFunds(ValueError):
    """Raised when a withdrawal or transfer would make a balance negative."""
    pass


class Ledger:
    def __init__(self):
        self._lock = threading.RLock()
        self._balances = {}
        self._history = {}

    @staticmethod
    def _is_valid_account(account) -> bool:
        return isinstance(account, str) and len(account) > 0

    @staticmethod
    def _is_valid_amount(amount) -> bool:
        # bool is a subclass of int in Python, so explicitly reject bool.
        return isinstance(amount, int) and not isinstance(amount, bool) and amount > 0

    @staticmethod
    def _is_valid_balance(balance) -> bool:
        return isinstance(balance, int) and not isinstance(balance, bool) and balance >= 0

    def open(self, account: str, balance: int = 0) -> None:
        with self._lock:
            if not self._is_valid_account(account):
                raise ValueError("account must be a non-empty string")
            if not self._is_valid_balance(balance):
                raise ValueError("balance must be a non-negative int (not bool)")
            if account in self._balances:
                raise ValueError(f"account already exists: {account!r}")
            self._balances[account] = balance
            self._history[account] = [("open", balance)]

    def balance(self, account) -> int:
        with self._lock:
            if account not in self._balances:
                raise KeyError(account)
            return self._balances[account]

    def deposit(self, account, amount) -> None:
        with self._lock:
            if account not in self._balances:
                raise KeyError(account)
            if not self._is_valid_amount(amount):
                raise ValueError("amount must be a positive int (not bool)")
            self._balances[account] += amount
            self._history[account].append(("deposit", amount))

    def withdraw(self, account, amount) -> None:
        with self._lock:
            if account not in self._balances:
                raise KeyError(account)
            if not self._is_valid_amount(amount):
                raise ValueError("amount must be a positive int (not bool)")
            if self._balances[account] - amount < 0:
                raise InsufficientFunds(
                    f"insufficient funds in account {account!r}"
                )
            self._balances[account] -= amount
            self._history[account].append(("withdraw", amount))

    def transfer(self, src, dst, amount) -> None:
        with self._lock:
            if src == dst:
                raise ValueError("src and dst must be different accounts")
            if src not in self._balances:
                raise KeyError(src)
            if dst not in self._balances:
                raise KeyError(dst)
            if not self._is_valid_amount(amount):
                raise ValueError("amount must be a positive int (not bool)")
            if self._balances[src] - amount < 0:
                raise InsufficientFunds(
                    f"insufficient funds in account {src!r}"
                )
            # All checks passed; apply both mutations atomically.
            self._balances[src] -= amount
            self._balances[dst] += amount
            self._history[src].append(("transfer_out", amount))
            self._history[dst].append(("transfer_in", amount))

    def total(self) -> int:
        with self._lock:
            return sum(self._balances.values())

    def history(self, account) -> list:
        with self._lock:
            if account not in self._history:
                raise KeyError(account)
            return list(self._history[account])
