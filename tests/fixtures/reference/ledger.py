import threading


class InsufficientFunds(ValueError):
    pass


def _amount(value, *, allow_zero=False):
    if type(value) is not int or value < 0 or (value == 0 and not allow_zero):
        raise ValueError("amount must be a positive int")
    return value


class Ledger:
    def __init__(self):
        self._lock = threading.RLock()
        self._balances = {}
        self._history = {}

    def open(self, account, balance=0):
        if not isinstance(account, str) or not account:
            raise ValueError("account must be a non-empty str")
        _amount(balance, allow_zero=True)
        with self._lock:
            if account in self._balances:
                raise ValueError("account exists")
            self._balances[account] = balance
            self._history[account] = [("open", balance)]

    def _require(self, account):
        if account not in self._balances:
            raise KeyError(account)

    def balance(self, account):
        with self._lock:
            self._require(account)
            return self._balances[account]

    def deposit(self, account, amount):
        _amount(amount)
        with self._lock:
            self._require(account)
            self._balances[account] += amount
            self._history[account].append(("deposit", amount))

    def withdraw(self, account, amount):
        _amount(amount)
        with self._lock:
            self._require(account)
            if self._balances[account] < amount:
                raise InsufficientFunds(account)
            self._balances[account] -= amount
            self._history[account].append(("withdraw", amount))

    def transfer(self, src, dst, amount):
        _amount(amount)
        if src == dst:
            raise ValueError("source and destination are the same")
        with self._lock:
            self._require(src)
            self._require(dst)
            if self._balances[src] < amount:
                raise InsufficientFunds(src)
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
