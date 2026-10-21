"""
solution.py

A simple in-memory text buffer with multi-level undo/redo support and
the ability to group several edits together so that they undo/redo as
a single unit.

Only the Python standard library is used.
"""

from __future__ import annotations

import contextlib
from typing import Iterator, List, Tuple, Union, Optional


# A record describing a single effective edit, in a form that lets us
# both undo and redo it:
#
#   ("insert", index, s)            -> forward action was: insert s at index
#   ("delete", start, end, deleted) -> forward action was: delete text[start:end]
#                                       (deleted == the text that was removed)
_InsertRecord = Tuple[str, int, str]
_DeleteRecord = Tuple[str, int, int, str]
_Record = Union[_InsertRecord, _DeleteRecord]


class TextBuffer:
    """A mutable text buffer supporting undo/redo and edit grouping."""

    def __init__(self, text: str = "") -> None:
        if not isinstance(text, str):
            raise ValueError("text must be a str")
        self._text: str = text

        # Each entry in these stacks is a *group* of records (a list),
        # representing one undoable/redoable step.
        self._undo_stack: List[List[_Record]] = []
        self._redo_stack: List[List[_Record]] = []

        # Support for nested group() calls: while _group_depth > 0 we are
        # inside a `with buf.group():` block (possibly nested) and new
        # records are collected into _current_group instead of being
        # pushed onto _undo_stack immediately.
        self._group_depth: int = 0
        self._current_group: Optional[List[_Record]] = None

    # ------------------------------------------------------------------
    # Public, read-only state
    # ------------------------------------------------------------------
    @property
    def text(self) -> str:
        return self._text

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _validate_int(value: int, name: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an int (not bool)")
        return value

    # ------------------------------------------------------------------
    # Editing API
    # ------------------------------------------------------------------
    def insert(self, index: int, s: str) -> None:
        index = self._validate_int(index, "index")
        if not isinstance(s, str):
            raise ValueError("s must be a str")
        if not (0 <= index <= len(self._text)):
            raise ValueError("index out of range")

        if s == "":
            return  # no
