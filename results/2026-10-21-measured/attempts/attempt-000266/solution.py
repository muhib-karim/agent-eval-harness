import threading


class InsufficientFunds(ValueError):
    pass


class Ledger:
    def __init__(self):
        self._balances = {}
        self._history = {}
        self._lock = threading.RLock()

    @staticmethod
    def _valid_int(value, minimum):
        return type(value) is int and value >= minimum

    def _require_account(self, account):
        if not isinstance(account, str) or account not in self._balances:
            raise KeyError(account)

    def open(self, account: str, balance: int = 0):
        if not isinstance(account, str) or not account:
            raise ValueError("account must be a non-empty string")
        if not self._valid_int(balance, 0):
            raise ValueError("balance must be a non-negative integer")

        with self._lock:
            if account in self._balances:
                raise ValueError("account already exists")
            self._balances[account] = balance
            self._history[account] = [("open", balance)]

    def balance(self, account) -> int:
        with self._lock:
            self._require_account(account)
            return self._balances[account]

    def deposit(self, account, amount):
        if not self._valid_int(amount, 1):
            raise ValueError("amount must be a positive integer")

        with self._lock:
            self._require_account(account)
            self._balances[account] += amount
            self._history[account].append(("deposit", amount))

    def withdraw(self, account, amount):
        if not self._valid_int(amount, 1):
            raise ValueError("amount must be a positive integer")

        with self._lock:
            self._require_account(account)
            if self._balances[account] < amount:
                raise InsufficientFunds("insufficient funds")
            self._balances[account] -= amount
            self._history[account].append(("withdraw", amount))

    def transfer(self, src, dst, amount):
        if src == dst:
            raise ValueError("source and destination must differ")
        if not self._valid_int(amount, 1):
            raise ValueError("amount must be a positive integer")

        with self._lock:
            self._require_account(src)
            self._require_account(dst)
            if self._balances[src] < amount:
                raise InsufficientFunds("insufficient funds")
            self._balances[src] -= amount
            self._balances[dst] += amount
            self._history[src].append(("transfer_out", amount))
            self._history[dst].append(("transfer_in", amount))

    def total(self) -> int:
        with self._lock:
            return sum(self._balances.values())

    def history(self, account) -> list:
        with self._lock:
            self._require_account(account)
            return list(self._history[account])
