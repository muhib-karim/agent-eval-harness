import threading


class InsufficientFunds(ValueError):
    pass


class Ledger:
    def __init__(self):
        self._lock = threading.RLock()
        self._balances = {}
        self._history = {}

    @staticmethod
    def _valid_int(value, minimum):
        return type(value) is int and value >= minimum

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
            return self._balances[account]

    def deposit(self, account, amount):
        if not self._valid_int(amount, 1):
            raise ValueError("amount must be a positive integer")

        with self._lock:
            self._balances[account] += amount
            self._history[account].append(("deposit", amount))

    def withdraw(self, account, amount):
        if not self._valid_int(amount, 1):
            raise ValueError("amount must be a positive integer")

        with self._lock:
            current = self._balances[account]
            if current < amount:
                raise InsufficientFunds("insufficient funds")
            self._balances[account] = current - amount
            self._history[account].append(("withdraw", amount))

    def transfer(self, src, dst, amount):
        if src == dst:
            raise ValueError("source and destination must differ")
        if not self._valid_int(amount, 1):
            raise ValueError("amount must be a positive integer")

        with self._lock:
            source_balance = self._balances[src]
            destination_balance = self._balances[dst]
            if source_balance < amount:
                raise InsufficientFunds("insufficient funds")

            self._balances[src] = source_balance - amount
            self._balances[dst] = destination_balance + amount
            self._history[src].append(("transfer_out", amount))
            self._history[dst].append(("transfer_in", amount))

    def total(self) -> int:
        with self._lock:
            return sum(self._balances.values())

    def history(self, account) -> list:
        with self._lock:
            return list(self._history[account])
