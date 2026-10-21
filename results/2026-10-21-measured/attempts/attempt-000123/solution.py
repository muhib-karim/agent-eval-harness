import threading


class InsufficientFunds(ValueError):
    pass


def _valid_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


class Ledger:
    def __init__(self):
        # A single lock guarantees atomic transfers, consistent snapshots,
        # and rules out lock-ordering deadlocks.
        self._lock = threading.RLock()
        self._balances = {}
        self._history = {}

    @staticmethod
    def _check_amount(amount):
        if not _valid_int(amount) or amount <= 0:
            raise ValueError("amount must be a positive int")

    def _require(self, account):
        try:
            if account in self._balances:
                return
        except TypeError:
            pass
        raise KeyError(account)

    def open(self, account, balance=0):
        if not isinstance(account, str) or not account:
            raise ValueError("account id must be a non-empty str")
        if not _valid_int(balance) or balance < 0:
            raise ValueError("balance must be a non-negative int")
        with self._lock:
            if account in self._balances:
                raise ValueError("account already exists")
            self._balances[account] = balance
            self._history[account] = [("open", balance)]

    def balance(self, account):
        with self._lock:
            self._require(account)
            return self._balances[account]

    def deposit(self, account, amount):
        self._check_amount(amount)
        with self._lock:
            self._require(account)
            self._balances[account] += amount
            self._history[account].append(("deposit", amount))

    def withdraw(self, account, amount):
        self._check_amount(amount)
        with self._lock:
            self._require(account)
            if self._balances[account] < amount:
                raise InsufficientFunds("insufficient funds")
            self._balances[account] -= amount
            self._history[account].append(("withdraw", amount))

    def transfer(self, src, dst, amount):
        self._check_amount(amount)
        with self._lock:
            try:
                same = src == dst
            except Exception:
                same = False
            if same:
                raise ValueError("src and dst must differ")
            self._require(src)
            self._require(dst)
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
            self._require(account)
            return list(self._history[account])
