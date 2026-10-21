import pytest
from solution import TextBuffer


def test_insert_and_delete() -> None:
    buf = TextBuffer("helo")
    buf.insert(3, "l")
    assert buf.text == "hello"
    buf.delete(0, 1)
    assert buf.text == "ello"
    buf.insert(4, "!")
    assert buf.text == "ello!"


def test_undo_redo_round_trip() -> None:
    buf = TextBuffer("abc")
    buf.insert(3, "def")
    buf.delete(0, 2)
    assert buf.text == "cdef"
    assert buf.undo() is True
    assert buf.text == "abcdef"
    assert buf.undo() is True
    assert buf.text == "abc"
    assert buf.redo() is True and buf.redo() is True
    assert buf.text == "cdef"


def test_nothing_to_undo_or_redo() -> None:
    buf = TextBuffer()
    assert buf.undo() is False
    assert buf.redo() is False
    assert buf.text == ""


def test_new_edit_clears_redo() -> None:
    buf = TextBuffer("a")
    buf.insert(1, "b")
    buf.undo()
    buf.insert(1, "c")
    assert buf.redo() is False
    assert buf.text == "ac"


def test_noop_edits_record_nothing_and_keep_redo() -> None:
    buf = TextBuffer("x")
    buf.insert(1, "y")
    buf.undo()
    buf.insert(0, "")
    buf.delete(1, 1)
    assert buf.redo() is True
    assert buf.text == "xy"
    assert buf.undo() is True and buf.undo() is False


def test_group_undoes_as_one_step() -> None:
    buf = TextBuffer("one")
    with buf.group():
        buf.insert(3, " two")
        buf.insert(7, " three")
        buf.delete(0, 4)
    assert buf.text == "two three"
    assert buf.undo() is True
    assert buf.text == "one"
    assert buf.redo() is True
    assert buf.text == "two three"


def test_nested_groups_merge() -> None:
    buf = TextBuffer()
    with buf.group():
        buf.insert(0, "a")
        with buf.group():
            buf.insert(1, "b")
        buf.insert(2, "c")
    assert buf.text == "abc"
    buf.undo()
    assert buf.text == ""
    assert buf.undo() is False


def test_empty_group_records_nothing() -> None:
    buf = TextBuffer("z")
    buf.insert(1, "!")
    with buf.group():
        pass
    assert buf.undo() is True
    assert buf.text == "z"


def test_failed_group_rolls_back() -> None:
    buf = TextBuffer("keep")
    with pytest.raises(RuntimeError), buf.group():
        buf.insert(4, "?")
        buf.delete(0, 1)
        raise RuntimeError("boom")
    assert buf.text == "keep"
    assert buf.undo() is False


@pytest.mark.parametrize(
    "call",
    [
        lambda b: b.insert(-1, "x"),
        lambda b: b.insert(4, "x"),
        lambda b: b.insert(True, "x"),
        lambda b: b.insert(0, 5),
        lambda b: b.delete(2, 1),
        lambda b: b.delete(0, 9),
        lambda b: b.delete(-1, 1),
        lambda b: b.delete(0.0, 1),
    ],
)
def test_invalid_arguments_leave_state(call: object) -> None:
    buf = TextBuffer("abc")
    with pytest.raises(ValueError):
        call(buf)  # type: ignore[operator]
    assert buf.text == "abc"
    assert buf.undo() is False


def test_text_is_read_only() -> None:
    buf = TextBuffer("a")
    assert buf.text == "a"
    with pytest.raises(AttributeError):
        buf.text = "b"  # type: ignore[misc]
    assert buf.text == "a"
