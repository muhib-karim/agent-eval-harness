solution.py
```python
from collections import deque
from contextlib import contextmanager
from typing import Optional, List, Tuple


class TextBuffer:
    def __init__(self, text: str = ""):
        if not isinstance(text, str):
            raise ValueError("Initial text must be a string")
        self._text = text
        self._undo_stack: deque = deque()
        self._redo_stack: deque = deque()
        self._group_stack: List[List[Tuple[str, int, str]]] = []
        self._in_group = False

    @property
    def text(self) -> str:
        return self._text

    def _validate_index(self, index: int, allow_end: bool = False) -> None:
        """Validate that index is a valid integer position."""
        if isinstance(index, bool):
            raise ValueError("Index must be an integer, not bool")
        if not isinstance(index, int):
            raise ValueError("Index must be an integer")
        max_index = len(self._text) if allow_end else len(self._text) - 1
        if not (0 <= index <= len(self._text) if allow_end else 0 <= index < len(self._text) or index == len(self._text)):
            raise ValueError("Index out of range")

    def _validate_range(self, start: int, end: int) -> None:
        """Validate a range [start:end]."""
        if isinstance(start, bool) or isinstance(end, bool):
            raise ValueError("Indices must be integers, not bool")
        if not isinstance(start, int) or not isinstance(end, int):
            raise ValueError("Indices must be integers")
        if not (0 <= start <= end <= len(self._text)):
            raise ValueError("Invalid range")

    def insert(self, index: int, s: str) -> None:
        """Insert string s before position index."""
        if isinstance(index, bool):
            raise ValueError("Index must be an integer, not bool")
        if not isinstance(index, int):
            raise ValueError("Index must be an integer")
        if not isinstance(s, str):
            raise ValueError("Inserted text must be a string")
        if not (0 <= index <= len(self._text)):
            raise ValueError("Index out of range")

        # No-op: inserting empty string records nothing
        if not s:
            return

        # Perform insertion
        self._text = self._text[:index] + s + self._text[index:]

        # Record operation
        operation = ("insert", index, s)
        self._record_operation(operation)

    def delete(self, start: int, end: int) -> None:
        """Delete text[start:end]."""
        if isinstance(start, bool) or isinstance(end, bool):
            raise ValueError("Indices must be integers, not bool")
        if not isinstance(start, int) or not isinstance(end, int):
            raise ValueError("Indices must be integers")
        if not (0 <= start <= end <= len(self._text)):
            raise ValueError("Invalid range")

        # No-op: deleting empty range records nothing
        if start == end:
            return

        # Get deleted text for undo
        deleted_text = self._text[start:end]

        # Perform deletion
        self._text = self._text[:start] + self._text[end:]

        # Record operation
        operation = ("delete", start, deleted_text)
        self._record_operation(operation)

    def _record_operation(self, operation: Tuple[str, int, str]) -> None:
        """Record an operation, managing undo/redo stacks and groups."""
        if self._group_stack:
            # Inside a group: add to current group
            self._group_stack[-1].append(operation)
        else:
            # Not in a group: add to undo stack and clear redo
            self._undo_stack.append([operation])
            self._redo_stack.clear()

    def undo(self) -> bool:
        """Undo the most recent edit or group."""
        if not self._undo_stack:
            return False

        operations = self._undo_stack.pop()
        redo_operations = []

        # Undo in reverse order
        for op_type, index, data in reversed(operations):
            if op_type == "insert":
                # Undo insert by deleting
                redo_operations.append(("insert", index, data))
                self._text = self._text[:index] + self._text[index + len(data):]
            elif op_type == "delete":
                # Undo delete by inserting
                redo_operations.append(("delete", index, data))
                self._text = self._text[:index] + data + self._text[index:]

        self._redo_stack.append(redo_operations)
        return True

    def redo(self) -> bool:
        """Redo the most recently undone edit or group."""
        if not self._redo_stack:
            return False

        operations = self._redo_stack.pop()
        undo_operations = []

        # Redo in order
        for op_type, index, data in operations:
            if op_type == "insert":
                # Redo insert
                undo_operations.append(("insert", index, data))
                self._text = self._text[:index] + data + self._text[index:]
            elif op_type == "delete":
                # Redo delete
                undo_operations.append(("delete", index, data))
                self._text = self._text[:index] + self._text[index + len(data):]

        self._undo_stack.append(undo_operations)
        return True

    @contextmanager
    def group(self):
        """Context manager for grouping edits."""
        # Save state in case we need to rollback
        saved_text = self._text
        self._group_stack.append([])

        try:
            yield
            # Check if group has any operations
            group_ops = self._group_stack.pop()
            if group_ops:
                # Record the group as a single undo step
                self._undo_stack.append(group_ops)
                self._redo_stack.clear()
            # If group is empty, don't record anything
        except Exception:
            # Rollback: restore text and discard group
            self._text = saved_text
            self._group_stack.pop()
            raise
