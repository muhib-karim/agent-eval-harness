"""
A thread-safe in-memory ledger implementation using only the Python standard library.
"""

import threading


class InsufficientFunds(ValueError):
    """Raised when a withdrawal or transfer would make a balance negative."""
    pass


class Ledger:
    def __init__(self):
        self._lock = threading.Lock()
        self._balances = {}
        self._history = {}

    # ---------- internal helpers ----------

    @staticmethod
    def _is_valid_account(account):
        return isinstance(account, str) and len(account) > 0

    @staticmethod
    def _is_valid_non_negative_int(value):
        return isinstance(value, int) and not isinstance(value, bool) and value >= 0

    @staticmethod
    def _is_valid_positive_int(value):
        return isinstance(value, int) and not isinstance(value, bool) and value > 0

    # ---------- public API ----------

    def open(self, account: str, balance: int = 0):
        if not self._is_valid_account(account):
            raise ValueError("Invalid account id")
        if not self._is_valid_non_negative_int(balance):
            raise ValueError("Invalid initial balance")

        with self._lock:
            if account in self._balances:
                raise ValueError("Account already exists")
            self._balances[account] = balance
            self._history[account] = [("open", balance)]

    def balance(self, account) -> int:
        with self._lock:
            if account not in self._balances:
                raise KeyError(account)
            return self._balances[account]

    def deposit(self, account, amount):
        if not self._is_valid_positive_int(amount):
            raise ValueError("Invalid deposit amount")

        with self._lock:
            if account not in self._balances:
                raise KeyError(account)
            self._balances[account] += amount
            self._history[account].append(("deposit", amount))

    def withdraw(self, account, amount):
        if not self._is_valid_positive_int(amount):
            raise ValueError("Invalid withdrawal amount")

        with self._lock:
            if account not in self._balances:
                raise KeyError(account)
            current = self._balances[account]
            if current - amount < 0:
                raise InsufficientFunds(
                    f"Insufficient funds in account {account!r}"
                )
            self._balances[account] = current - amount
            self._history[account].append(("withdraw", amount))

    def transfer(self, src, dst, amount):
        if src == dst:
            raise ValueError("Source and destination accounts must differ")
        if not self._is_valid_positive_int(amount):
            raise ValueError("Invalid transfer amount")

        with self._lock:
            if src not in self._balances:
                raise KeyError(src)
            if dst not in self._balances:
                raise KeyError(dst)

            src_balance = self._balances[src]
            if src_balance - amount < 0:
                raise InsufficientFunds(
                    f"Insufficient funds in account {src!r}"
                )

            self._balances[src] = src_balance - amount
            self._balances[dst] += amount

            self._history[src].append(("transfer_out", amount))
            self._history[dst].append(("transfer_in", amount))

    def total(self) -> int:
        with self._lock:
            return sum(self._balances.values())

    def history(self, account):
        with self._lock:
            if account not in self._history:
                raise KeyError(account)
            return list(self._history[account])
