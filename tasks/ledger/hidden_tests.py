import contextlib
import threading

import pytest
from solution import InsufficientFunds, Ledger


def make(**balances: int) -> Ledger:
    ledger = Ledger()
    for name, amount in balances.items():
        ledger.open(name, amount)
    return ledger


def test_open_deposit_withdraw_balance() -> None:
    ledger = make(a=10)
    ledger.deposit("a", 5)
    ledger.withdraw("a", 3)
    assert ledger.balance("a") == 12
    ledger.open("b")
    assert ledger.balance("b") == 0


@pytest.mark.parametrize("args", [("", 0), ("x", -1), ("x", True), ("x", 1.5), (3, 0)])
def test_open_validation(args: tuple[object, object]) -> None:
    with pytest.raises(ValueError):
        Ledger().open(*args)  # type: ignore[arg-type]


def test_duplicate_open_and_unknown_account() -> None:
    ledger = make(a=1)
    with pytest.raises(ValueError):
        ledger.open("a")
    with pytest.raises(KeyError):
        ledger.balance("missing")
    with pytest.raises(KeyError):
        ledger.deposit("missing", 1)


@pytest.mark.parametrize("amount", [0, -5, True, 2.0])
def test_amount_validation(amount: object) -> None:
    ledger = make(a=10, b=0)
    with pytest.raises(ValueError):
        ledger.deposit("a", amount)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        ledger.transfer("a", "b", amount)  # type: ignore[arg-type]
    assert ledger.balance("a") == 10


def test_insufficient_funds_changes_nothing() -> None:
    ledger = make(a=5, b=0)
    with pytest.raises(InsufficientFunds):
        ledger.withdraw("a", 6)
    with pytest.raises(InsufficientFunds):
        ledger.transfer("a", "b", 6)
    assert issubclass(InsufficientFunds, ValueError)
    assert (ledger.balance("a"), ledger.balance("b")) == (5, 0)
    assert ledger.history("a") == [("open", 5)]


def test_transfer_and_history() -> None:
    ledger = make(a=10, b=1)
    ledger.transfer("a", "b", 4)
    assert (ledger.balance("a"), ledger.balance("b"), ledger.total()) == (6, 5, 11)
    assert ledger.history("a") == [("open", 10), ("transfer_out", 4)]
    assert ledger.history("b") == [("open", 1), ("transfer_in", 4)]
    ledger.history("a").append(("hack", 1))
    assert len(ledger.history("a")) == 2


def test_transfer_validation() -> None:
    ledger = make(a=10)
    with pytest.raises(ValueError):
        ledger.transfer("a", "a", 1)
    with pytest.raises(KeyError):
        ledger.transfer("a", "missing", 1)
    assert ledger.balance("a") == 10


def test_concurrent_deposits_are_not_lost() -> None:
    ledger = make(a=0)

    def work() -> None:
        for _ in range(2000):
            ledger.deposit("a", 1)

    threads = [threading.Thread(target=work) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert ledger.balance("a") == 16000
    assert len(ledger.history("a")) == 16001


def test_opposite_transfers_do_not_deadlock_and_conserve_money() -> None:
    ledger = make(a=1000, b=1000, c=1000)
    errors: list[BaseException] = []
    snapshots: list[int] = []

    def mover(src: str, dst: str) -> None:
        try:
            for _ in range(1500):
                with contextlib.suppress(InsufficientFunds):
                    ledger.transfer(src, dst, 1)
        except BaseException as exc:  # pragma: no cover - surfaced below
            errors.append(exc)

    def watcher() -> None:
        for _ in range(300):
            snapshots.append(ledger.total())

    pairs = [("a", "b"), ("b", "a"), ("b", "c"), ("c", "a"), ("a", "c"), ("c", "b")]
    threads = [threading.Thread(target=mover, args=pair) for pair in pairs]
    threads.append(threading.Thread(target=watcher))
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=15)
    assert not any(thread.is_alive() for thread in threads), "deadlock"
    assert errors == []
    assert set(snapshots) == {3000}
    assert ledger.total() == 3000
    assert min(ledger.balance(x) for x in "abc") >= 0
