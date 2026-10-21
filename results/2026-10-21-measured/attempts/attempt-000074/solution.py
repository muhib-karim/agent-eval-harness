"""Thread-safe in-memory ledger."""

import threading


class InsufficientFunds(ValueError):
    """Raised when a withdrawal or transfer would make a balance negative."""


def _check_account_id(account):
    if not isinstance(account, str) or not account:
        raise ValueError("account id must be a non-empty string")


def _check_amount(amount, *, allow_zero=False):
    if isinstance(amount, bool) or not isinstance(amount, int):
        raise ValueError("amount must be an int")
    if allow_zero:
        if amount < 0:
            raise ValueError("amount must be non-negative")
    else:
        if amount <= 0:
            raise ValueError("amount must be positive")


class Ledger:
    """An in-memory ledger whose every method is safe to call concurrently.

    A single lock guards all state. Every public operation is executed
    entirely under that lock, which makes each operation atomic, makes
    ``total()`` a consistent snapshot, and rules out deadlocks (there is
    never more than one lock to acquire).
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._balances = {}
        self._history = {}

    # ------------------------------------------------------------------ #
    # helpers (must be called with the lock held)
    # ------------------------------------------------------------------ #
    def _require(self, account):
        if account not in self._balances:
            raise KeyError(account)

    # ------------------------------------------------------------------ #
    # public API
    # ------------------------------------------------------------------ #
    def open(self, account, balance=0):
        _check_account_id(account)
        _check_amount(balance, allow_zero=True)
        with self._lock:
            if account in self._balances:
                raise ValueError("account already exists: %r" % (account,))
            self._balances[account] = balance
            self._history[account] = [("open", balance)]

    def balance(self, account):
        with self._lock:
            self._require(account)
            return self._balances[account]

    def deposit(self, account, amount):
        _check_amount(amount)
        with self._lock:
            self._require(account)
            self._balances[account] += amount
            self._history[account].append(("deposit", amount))

    def withdraw(self, account, amount):
        _check_amount(amount)
        with self._lock:
            self._require(account)
            current = self._balances[account]
            if current - amount < 0:
                raise InsufficientFunds(
                    "insufficient funds in %r: balance %d, requested %d"
                    % (account, current, amount)
                )
            self._balances[account] = current - amount
            self._history[account].append(("withdraw", amount))

    def transfer(self, src, dst, amount):
        _check_amount(amount)
        if src == dst:
            raise ValueError("source and destination must differ")
        with self._lock:
            self._require(src)
            self._require(dst)
            current = self._balances[src]
            if current - amount < 0:
                raise InsufficientFunds(
                    "insufficient funds in %r: balance %d, requested %d"
                    % (src, current, amount)
                )
            self._balances[src] = current - amount
            self._balances[dst] += amount
            self._history[src].append(("transfer_out", amount))
            self._history[dst].append(("transfer_in", amount))

    def total(self):
        with self._lock:
            return sum(self._balances.values())

    def history(self, account):
        with self._lock:
            self._require(account)
            return list(self._history[account])
