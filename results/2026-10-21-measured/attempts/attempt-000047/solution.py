from contextlib import contextmanager


class TextBuffer:
    def __init__(self, text: str = ""):
        if not isinstance(text, str):
            raise ValueError("text must be a str")
        self._text = text
        self._undo = []
        self._redo = []
        self._depth = 0
        self._pending = []

    @property
    def text(self) -> str:
        return self._text

    @staticmethod
    def _is_int(x):
        return isinstance(x, int) and not isinstance(x, bool)

    # low-level application of operations
    def _apply(self, op):
        kind, idx, s = op
        if kind == "ins":
            self._text = self._text[:idx] + s + self._text[idx:]
        else:
            self._text = self._text[:idx] + self._text[idx + len(s):]

    def _revert(self, op):
        kind, idx, s = op
        if kind == "ins":
            self._text = self._text[:idx] + self._text[idx + len(s):]
        else:
            self._text = self._text[:idx] + s + self._text[idx:]

    def _record(self, op):
        self._apply(op)
        if self._depth > 0:
            self._pending.append(op)
        else:
            self._undo.append((op,))
            self._redo.clear()

    def insert(self, index: int, s: str) -> None:
        if not self._is_int(index):
            raise ValueError("index must be an int")
        if not isinstance(s, str):
            raise ValueError("s must be a str")
        if index < 0 or index > len(self._text):
            raise ValueError("index out of range")
        if s == "":
            return
        self._record(("ins", index, s))

    def delete(self, start: int, end: int) -> None:
        if not self._is_int(start) or not self._is_int(end):
            raise ValueError("positions must be ints")
        if start < 0 or end > len(self._text) or start > end:
            raise ValueError("invalid range")
        if start == end:
            return
        self._record(("del", start, self._text[start:end]))

    def undo(self) -> bool:
        if self._depth > 0:
            raise RuntimeError("cannot undo inside a group")
        if not self._undo:
            return False
        grp = self._undo.pop()
        for op in reversed(grp):
            self._revert(op)
        self._redo.append(grp)
        return True

    def redo(self) -> bool:
        if self._depth > 0:
            raise RuntimeError("cannot redo inside a group")
        if not self._redo:
            return False
        grp = self._redo.pop()
        for op in grp:
            self._apply(op)
        self._undo.append(grp)
        return True

    @contextmanager
    def group(self):
        mark = len(self._pending)
        self._depth += 1
        try:
            yield self
        except BaseException:
            # roll back edits made inside this block
            while len(self._pending) > mark:
                self._revert(self._pending.pop())
            self._depth -= 1
            if self._depth == 0:
                self._pending = []
            raise
        self._depth -= 1
        if self._depth == 0:
            ops = self._pending
            self._pending = []
            if ops:
                self._undo.append(tuple(ops))
                self._redo.clear()
