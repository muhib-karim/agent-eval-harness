from contextlib import contextmanager


class TextBuffer:
    """A text buffer with insert/delete operations, unbounded undo/redo,
    and grouping of edits into single undoable steps."""

    def __init__(self, text: str = ""):
        if not isinstance(text, str):
            raise ValueError("text must be a str")
        self._text = text
        self._undo = []          # list of groups; each group is a list of edits
        self._redo = []          # list of groups
        self._depth = 0          # nesting depth of group() blocks
        self._pending = None     # edits recorded inside the current outermost group

    # ------------------------------------------------------------------ #
    # Properties
    # ------------------------------------------------------------------ #
    @property
    def text(self) -> str:
        return self._text

    # ------------------------------------------------------------------ #
    # Validation helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _check_int(value, name):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"{name} must be an int")

    def _check_position(self, index, name="index"):
        self._check_int(index, name)
        if index < 0 or index > len(self._text):
            raise ValueError(f"{name} out of range")

    # ------------------------------------------------------------------ #
    # Raw (unrecorded) operations
    # ------------------------------------------------------------------ #
    def _apply(self, edit):
        kind, index, s = edit
        if kind == "insert":
            self._text = self._text[:index] + s + self._text[index:]
        else:  # "delete"
            self._text = self._text[:index] + self._text[index + len(s):]

    def _revert(self, edit):
        kind, index, s = edit
        if kind == "insert":
            self._text = self._text[:index] + self._text[index + len(s):]
        else:  # "delete"
            self._text = self._text[:index] + s + self._text[index:]

    def _record(self, edit):
        if self._depth > 0:
            self._pending.append(edit)
        else:
            self._undo.append([edit])
            self._redo.clear()

    # ------------------------------------------------------------------ #
    # Public edit operations
    # ------------------------------------------------------------------ #
    def insert(self, index: int, s: str) -> None:
        self._check_position(index, "index")
        if not isinstance(s, str):
            raise ValueError("s must be a str")
        if s == "":
            return
        edit = ("insert", index, s)
        self._apply(edit)
        self._record(edit)

    def delete(self, start: int, end: int) -> None:
        self._check_int(start, "start")
        self._check_int(end, "end")
        n = len(self._text)
        if start < 0 or end > n or start > end:
            raise ValueError("invalid range")
        if start == end:
            return
        edit = ("delete", start, self._text[start:end])
        self._apply(edit)
        self._record(edit)

    # ------------------------------------------------------------------ #
    # Undo / redo
    # ------------------------------------------------------------------ #
    def undo(self) -> bool:
        if not self._undo:
            return False
        group = self._undo.pop()
        for edit in reversed(group):
            self._revert(edit)
        self._redo.append(group)
        return True

    def redo(self) -> bool:
        if not self._redo:
            return False
        group = self._redo.pop()
        for edit in group:
            self._apply(edit)
        self._undo.append(group)
        return True

    # ------------------------------------------------------------------ #
    # Grouping
    # ------------------------------------------------------------------ #
    @contextmanager
    def group(self):
        if self._depth == 0:
            self._pending = []
        self._depth += 1
        try:
            yield self
        except BaseException:
            self._depth -= 1
            if self._depth == 0:
                pending = self._pending
                self._pending = None
                for edit in reversed(pending):
                    self._revert(edit)
            raise
        else:
            self._depth -= 1
            if self._depth == 0:
                pending = self._pending
                self._pending = None
                if pending:
                    self._undo.append(pending)
                    self._redo.clear()
