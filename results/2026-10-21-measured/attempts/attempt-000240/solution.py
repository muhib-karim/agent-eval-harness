from collections import deque
from contextlib import contextmanager
from typing import Optional, Deque, List, Tuple, Any


class TextBuffer:
    def __init__(self, text: str = ""):
        if not isinstance(text, str):
            raise ValueError("Initial text must be a string")
        self._text = text
        self._undo_stack: Deque[List[Tuple[str, int, str]]] = deque()  # Stack of edit groups
        self._redo_stack: Deque[List[Tuple[str, int, str]]] = deque()  # Stack of redo groups
        self._group_stack: List[List[Tuple[str, int, str]]] = []  # For nested groups
        self._in_group = False

    @property
    def text(self) -> str:
        return self._text

    def _validate_index(self, index: int) -> None:
        """Validate that index is a valid integer."""
        if isinstance(index, bool) or not isinstance(index, int):
            raise ValueError("Index must be an integer")

    def _validate_indices(self, start: int, end: int, allow_equal: bool = True) -> None:
        """Validate start and end indices."""
        self._validate_index(start)
        self._validate_index(end)
        if start < 0 or end < 0 or start > len(self._text) or end > len(self._text):
            raise ValueError("Indices out of range")
        if start > end:
            raise ValueError("Start index cannot be greater than end index")

    def insert(self, index: int, s: str) -> None:
        """Insert string s before position index."""
        self._validate_index(index)
        if not isinstance(s, str):
            raise ValueError("Inserted text must be a string")
        if index < 0 or index > len(self._text):
            raise ValueError("Index out of range")

        # No-op: inserting empty string
        if len(s) == 0:
            return

        # Perform insertion
        self._text = self._text[:index] + s + self._text[index:]

        # Record edit
        self._record_edit("insert", index, s)

    def delete(self, start: int, end: int) -> None:
        """Delete text[start:end]."""
        self._validate_indices(start, end)

        # No-op: deleting empty range
        if start == end:
            return

        # Get deleted text for undo
        deleted_text = self._text[start:end]

        # Perform deletion
        self._text = self._text[:start] + self._text[end:]

        # Record edit
        self._record_edit("delete", start, deleted_text)

    def _record_edit(self, op: str, index: int, data: str) -> None:
        """Record an edit operation."""
        edit = (op, index, data)

        if self._in_group:
            # Add to current group
            self._group_stack[-1].append(edit)
        else:
            # Clear redo stack and add to undo stack
            self._redo_stack.clear()
            self._undo_stack.append([edit])

    def undo(self) -> bool:
        """Undo the most recent edit or group."""
        if not self._undo_stack:
            return False

        # Pop the most recent group
        group = self._undo_stack.pop()

        # Apply edits in reverse order
        for op, index, data in reversed(group):
            if op == "insert":
                # Undo insert: delete the inserted text
                self._text = self._text[:index] + self._text[index + len(data):]
            elif op == "delete":
                # Undo delete: insert the deleted text
                self._text = self._text[:index] + data + self._text[index:]

        # Push to redo stack
        self._redo_stack.append(group)
        return True

    def redo(self) -> bool:
        """Redo the most recently undone edit or group."""
        if not self._redo_stack:
            return False

        # Pop the most recent group
        group = self._redo_stack.pop()

        # Apply edits in forward order
        for op, index, data in group:
            if op == "insert":
                # Redo insert: insert the text
                self._text = self._text[:index] + data + self._text[index:]
            elif op == "delete":
                # Redo delete: delete the text
                self._text = self._text[:index] + self._text[index + len(data):]

        # Push to undo stack
        self._undo_stack.append(group)
        return True

    @contextmanager
    def group(self):
        """Context manager for grouping edits."""
        # Save current state
        saved_text = self._text

        # Start grouping
        self._group_stack.append([])
        self._in_group = True

        try:
            yield
        except Exception:
            # Rollback on exception
            self._text = saved_text
            self._group_stack.pop()
            self._in_group = len(self._group_stack) > 0
            raise
        else:
            # Commit the group
            group = self._group_stack.pop()
            self._in_group = len(self._group_stack) > 0

            # Only record non-empty groups
            if group:
                if self._in_group:
                    # Merge into parent group
                    self._group_stack[-1].extend(group)
                else:
                    # Clear redo stack and add to undo stack
                    self._redo_stack.clear()
                    self._undo_stack.append(group)
