import threading


class InsufficientFunds(ValueError):
    """Raised when a withdrawal or transfer would make a balance negative."""


def _check_account_id(account):
    if not isinstance(account, str) or account == "":
        raise ValueError("account id must be a non-empty str")


def _check_non_negative_int(value, name):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an int")
    if value < 0:
        raise ValueError(f"{name} must be non-negative")


def _check_positive_int(value, name):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an int")
    if value <= 0:
        raise ValueError(f"{name} must be positive")


class Ledger:
    """Thread-safe in-memory ledger.

    A single lock guards all state. Every operation (including transfers and
    total()) runs entirely under that lock, so operations are atomic, total()
    always observes a consistent snapshot, and no lock-ordering issues can
    arise (hence no deadlocks for opposite-direction transfers).
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._balances = {}
        self._history = {}

    # ------------------------------------------------------------------ open
    def open(self, account, balance=0):
        _check_account_id(account)
        _check_non_negative_int(balance, "balance")
        with self._lock:
            if account in self._balances:
                raise ValueError(f"account {account!r} already exists")
            self._balances[account] = balance
            self._history[account] = [("open", balance)]

    # --------------------------------------------------------------- balance
    def balance(self, account):
        with self._lock:
            if account not in self._balances:
                raise KeyError(account)
            return self._balances[account]

    # --------------------------------------------------------------- deposit
    def deposit(self, account, amount):
        _check_positive_int(amount, "amount")
        with self._lock:
            if account not in self._balances:
                raise KeyError(account)
            self._balances[account] += amount
            self._history[account].append(("deposit", amount))

    # -------------------------------------------------------------- withdraw
    def withdraw(self, account, amount):
        _check_positive_int(amount, "amount")
        with self._lock:
            if account not in self._balances:
                raise KeyError(account)
            current = self._balances[account]
            if current - amount < 0:
                raise InsufficientFunds(
                    f"account {account!r} has {current}, cannot withdraw {amount}"
                )
            self._balances[account] = current - amount
            self._history[account].append(("withdraw", amount))

    # -------------------------------------------------------------- transfer
    def transfer(self, src, dst, amount):
        _check_positive_int(amount, "amount")
        if src == dst:
            raise ValueError("source and destination must differ")
        with self._lock:
            if src not in self._balances:
                raise KeyError(src)
            if dst not in self._balances:
                raise KeyError(dst)
            src_balance = self._balances[src]
            if src_balance - amount < 0:
                raise InsufficientFunds(
                    f"account {src!r} has {src_balance}, cannot transfer {amount}"
                )
            # All validation passed: apply both sides atomically.
            self._balances[src] = src_balance - amount
            self._balances[dst] += amount
            self._history[src].append(("transfer_out", amount))
            self._history[dst].append(("transfer_in", amount))

    # ----------------------------------------------------------------- total
    def total(self):
        with self._lock:
            return sum(self._balances.values())

    # --------------------------------------------------------------- history
    def history(self, account):
        with self._lock:
            if account not in self._history:
                raise KeyError(account)
            return list(self._history[account])
