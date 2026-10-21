solution.py

from contextlib import contextmanager
from typing import List, Tuple

class TextBuffer:
    def __init__(self, text: str = ""):
        if not isinstance(text, str):
            raise ValueError("text must be a string")
        self._text = text
        self._undo_stack: List[str] = []
        self._redo_stack: List[str] = []
        self._group_depth = 0
        self._group_start_text: str = ""

    @property
    def text(self) -> str:
        return self._text

    def _validate_position(self, pos: int) -> None:
        """Validate that pos is a valid integer."""
        if isinstance(pos, bool) or not isinstance(pos, int):
            raise ValueError("position must be an integer")

    def _validate_range(self, start: int, end: int) -> None:
        """Validate start and end positions."""
        self._validate_position(start)
        self._validate_position(end)
        if start < 0 or end < 0 or start > len(self._text) or end > len(self._text):
            raise ValueError("position out of range")
        if start > end:
            raise ValueError("start cannot be greater than end")

    def insert(self, index: int, s: str) -> None:
        """Insert string s before position index."""
        self._validate_position(index)
        if not isinstance(s, str):
            raise ValueError("s must be a string")
        if index < 0 or index > len(self._text):
            raise ValueError("index out of range")

        # No-op for empty string - don't record
        if not s:
            return

        # This is an effective edit
        if self._group_depth == 0:
            self._undo_stack.append(self._text)
            self._redo_stack.clear()

        self._text = self._text[:index] + s + self._text[index:]

    def delete(self, start: int, end: int) -> None:
        """Delete text[start:end]."""
        self._validate_range(start, end)

        # No-op for empty range - don't record
        if start == end:
            return

        # This is an effective edit
        if self._group_depth == 0:
            self._undo_stack.append(self._text)
            self._redo_stack.clear()

        self._text = self._text[:start] + self._text[end:]

    def undo(self) -> bool:
        """Undo the most recent edit or group. Returns False if nothing to undo."""
        if not self._undo_stack:
            return False

        self._redo_stack.append(self._text)
        self._text = self._undo_stack.pop()
        return True

    def redo(self) -> bool:
        """Redo the most recently undone edit or group. Returns False if none."""
        if not self._redo_stack:
            return False

        self._undo_stack.append(self._text)
        self._text = self._redo_stack.pop()
        return True

    @contextmanager
    def group(self):
        """Context manager for grouping edits into a single undo/redo step."""
        self._group_depth += 1

        # Only the outermost group records the starting state
        if self._group_depth == 1:
            self._group_start_text = self._text

        try:
            yield
        except Exception:
            # Rollback: restore to state before group started
            self._text = self._group_start_text
            self._group_depth -= 1
            raise

        # Normal completion of group
        self._group_depth -= 1

        # Only the outermost group (depth becomes 0) records the change
        if self._group_depth == 0:
            # Only record if there was an effective change
            if self._text != self._group_start_text:
                self._undo_stack.append(self._group_start_text)
                self._redo_stack.clear()
