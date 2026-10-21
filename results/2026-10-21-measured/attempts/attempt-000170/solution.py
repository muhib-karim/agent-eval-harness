import threading


class InsufficientFunds(ValueError):
    pass


class Ledger:
    def __init__(self):
        self._lock = threading.Lock()
        self._balances = {}
        self._history = {}

    @staticmethod
    def _check_account_id(account):
        if not isinstance(account, str) or account == "":
            raise ValueError("account must be a non-empty string")

    @staticmethod
    def _check_amount(amount):
        if isinstance(amount, bool) or not isinstance(amount, int):
            raise ValueError("amount must be a positive int")
        if amount <= 0:
            raise ValueError("amount must be a positive int")

    @staticmethod
    def _check_balance(balance):
        if isinstance(balance, bool) or not isinstance(balance, int):
            raise ValueError("balance must be a non-negative int")
        if balance < 0:
            raise ValueError("balance must be a non-negative int")

    def open(self, account: str, balance: int = 0):
        self._check_account_id(account)
        self._check_balance(balance)
        with self._lock:
            if account in self._balances:
                raise ValueError(f"account {account!r} already exists")
            self._balances[account] = balance
            self._history[account] = [("open", balance)]

    def balance(self, account) -> int:
        with self._lock:
            if account not in self._balances:
                raise KeyError(account)
            return self._balances[account]

    def deposit(self, account, amount):
        self._check_amount(amount)
        with self._lock:
            if account not in self._balances:
                raise KeyError(account)
            self._balances[account] += amount
            self._history[account].append(("deposit", amount))

    def withdraw(self, account, amount):
        self._check_amount(amount)
        with self._lock:
            if account not in self._balances:
                raise KeyError(account)
            if self._balances[account] - amount < 0:
                raise InsufficientFunds(
                    f"insufficient funds in account {account!r}"
                )
            self._balances[account] -= amount
            self._history[account].append(("withdraw", amount))

    def transfer(self, src, dst, amount):
        self._check_amount(amount)
        if src == dst:
            raise ValueError("src and dst must be different accounts")
        with self._lock:
            if src not in self._balances:
                raise KeyError(src)
            if dst not in self._balances:
                raise KeyError(dst)
            if self._balances[src] - amount < 0:
                raise InsufficientFunds(
                    f"insufficient funds in account {src!r}"
                )
            self._balances[src] -= amount
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
