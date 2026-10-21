import threading


class InsufficientFunds(ValueError):
    pass


def _is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def _check_amount(amount):
    if not _is_int(amount) or amount <= 0:
        raise ValueError("amount must be a positive int")


class Ledger:
    def __init__(self):
        self._lock = threading.Lock()
        self._balances = {}
        self._history = {}

    def _require(self, account):
        if account not in self._balances:
            raise KeyError(account)

    def open(self, account, balance=0):
        if not isinstance(account, str) or not account:
            raise ValueError("account id must be a non-empty str")
        if not _is_int(balance) or balance < 0:
            raise ValueError("balance must be a non-negative int")
        with self._lock:
            if account in self._balances:
                raise ValueError("account already exists")
            self._balances[account] = balance
            self._history[account] = [("open", balance)]

    def balance(self, account):
        with self._lock:
            try:
                return self._balances[account]
            except (KeyError, TypeError):
                raise KeyError(account)

    def deposit(self, account, amount):
        _check_amount(amount)
        with self._lock:
            self._require_safe(account)
            self._balances[account] += amount
            self._history[account].append(("deposit", amount))

    def withdraw(self, account, amount):
        _check_amount(amount)
        with self._lock:
            self._require_safe(account)
            if self._balances[account] < amount:
                raise InsufficientFunds("insufficient funds")
            self._balances[account] -= amount
            self._history[account].append(("withdraw", amount))

    def transfer(self, src, dst, amount):
        _check_amount(amount)
        with self._lock:
            self._require_safe(src)
            self._require_safe(dst)
            if src == dst:
                raise ValueError("src and dst must differ")
            if self._balances[src] < amount:
                raise InsufficientFunds("insufficient funds")
            self._balances[src] -= amount
            self._balances[dst] += amount
            self._history[src].append(("transfer_out", amount))
            self._history[dst].append(("transfer_in", amount))

    def total(self):
        with self._lock:
            return sum(self._balances.values())

    def history(self, account):
        with self._lock:
            self._require_safe(account)
            return list(self._history[account])

    def _require_safe(self, account):
        try:
            present = account in self._balances
        except TypeError:
            present = False
        if not present:
            raise KeyError(account)
