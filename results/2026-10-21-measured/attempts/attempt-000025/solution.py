import threading

__all__ = ["InsufficientFunds", "Ledger"]


class InsufficientFunds(ValueError):
    """Raised when an operation would make a balance negative."""


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _check_amount(amount):
    if not _is_int(amount) or amount <= 0:
        raise ValueError("amount must be a positive int")


class Ledger:
    """Thread-safe in-memory ledger.

    A single re-entrant lock guards all state, so every operation is atomic
    with respect to every other. Because there is only one lock, transfers
    in opposite directions can never deadlock, and total() always observes
    a consistent snapshot.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._balances = {}
        self._history = {}

    def _require(self, account):
        # Must be called with the lock held.
        if not isinstance(account, str) or account not in self._balances:
            raise KeyError(account)

    def open(self, account, balance=0):
        if not isinstance(account, str) or not account:
            raise ValueError("account id must be a non-empty str")
        if not _is_int(balance) or balance < 0:
            raise ValueError("balance must be a non-negative int")
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
            if self._balances[account] < amount:
                raise InsufficientFunds(
                    "insufficient funds in %r" % (account,))
            self._balances[account] -= amount
            self._history[account].append(("withdraw", amount))

    def transfer(self, src, dst, amount):
        _check_amount(amount)
        with self._lock:
            self._require(src)
            self._require(dst)
            if src == dst:
                raise ValueError("cannot transfer to the same account")
            if self._balances[src] < amount:
                raise InsufficientFunds("insufficient funds in %r" % (src,))
            self._balances[src] -= amount
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
