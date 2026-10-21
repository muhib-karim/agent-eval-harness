from contextlib import contextmanager


class TextBuffer:
    """A text buffer with insert/delete, unbounded undo/redo and grouping."""

    def __init__(self, text: str = ""):
        if not isinstance(text, str):
            raise ValueError("text must be a str")
        self._text = text
        self._undo = []       # list of groups; each group is a list of edits
        self._redo = []
        self._depth = 0       # group nesting depth
        self._current = None  # edits recorded in the current outermost group

    # ------------------------------------------------------------------ #
    @property
    def text(self) -> str:
        return self._text

    # ------------------------------------------------------------------ #
    @staticmethod
    def _check_int(value, name):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an int")

    def _record(self, edit):
        if self._depth > 0:
            self._current.append(edit)
        else:
            self._undo.append([edit])
            self._redo.clear()

    # ------------------------------------------------------------------ #
    def insert(self, index: int, s: str) -> None:
        self._check_int(index, "index")
        if not isinstance(s, str):
            raise ValueError("s must be a str")
        if index < 0 or index > len(self._text):
            raise ValueError("index out of range")
        if s == "":
            return
        self._text = self._text[:index] + s + self._text[index:]
        self._record(("insert", index, s))

    def delete(self, start: int, end: int) -> None:
        self._check_int(start, "start")
        self._check_int(end, "end")
        if start < 0 or end > len(self._text) or start > end:
            raise ValueError("invalid range")
        if start == end:
            return
        removed = self._text[start:end]
        self._text = self._text[:start] + self._text[end:]
        self._record(("delete", start, removed))

    # ------------------------------------------------------------------ #
    def _apply(self, edit):
        kind, pos, s = edit
        if kind == "insert":
            self._text = self._text[:pos] + s + self._text[pos:]
        else:
            self._text = self._text[:pos] + self._text[pos + len(s):]

    def _revert(self, edit):
        kind, pos, s = edit
        if kind == "insert":
            self._text = self._text[:pos] + self._text[pos + len(s):]
        else:
            self._text = self._text[:pos] + s + self._text[pos:]

    def undo(self) -> bool:
        if self._depth > 0 or not self._undo:
            return False
        group = self._undo.pop()
        for edit in reversed(group):
            self._revert(edit)
        self._redo.append(group)
        return True

    def redo(self) -> bool:
        if self._depth > 0 or not self._redo:
            return False
        group = self._redo.pop()
        for edit in group:
            self._apply(edit)
        self._undo.append(group)
        return True

    # ------------------------------------------------------------------ #
    @contextmanager
    def group(self):
        if self._depth == 0:
            self._current = []
        start_len = len(self._current)
        self._depth += 1
        try:
            yield self
        except BaseException:
            # Roll back edits made inside this block, record nothing.
            while len(self._current) > start_len:
                self._revert(self._current.pop())
            raise
        finally:
            self._depth -= 1
            if self._depth == 0:
                edits = self._current
                self._current = None
                if edits:
                    self._undo.append(edits)
                    self._redo.clear()
