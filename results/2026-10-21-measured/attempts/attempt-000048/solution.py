from contextlib import contextmanager


class TextBuffer:
    def __init__(self, text: str = ""):
        if not isinstance(text, str):
            raise ValueError("text must be a str")
        self._text = text
        self._undo = []      # list of tuples of ops
        self._redo = []      # list of tuples of ops
        self._depth = 0
        self._pending = []   # ops of current outermost group

    @property
    def text(self) -> str:
        return self._text

    # ----- validation helpers -----
    @staticmethod
    def _is_int(v):
        return isinstance(v, int) and not isinstance(v, bool)

    # ----- low-level application -----
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
        self._redo = []
        if self._depth > 0:
            self._pending.append(op)
        else:
            self._undo.append((op,))

    # ----- public edit API -----
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

    def _flush_pending(self):
        if self._pending:
            self._undo.append(tuple(self._pending))
            self._pending = []

    def undo(self) -> bool:
        if self._depth > 0:
            self._flush_pending()
        if not self._undo:
            return False
        step = self._undo.pop()
        for op in reversed(step):
            self._revert(op)
        self._redo.append(step)
        return True

    def redo(self) -> bool:
        if self._depth > 0:
            self._flush_pending()
        if not self._redo:
            return False
        step = self._redo.pop()
        for op in step:
            self._apply(op)
        self._undo.append(step)
        return True

    @contextmanager
    def group(self):
        snapshot = (
            self._text,
            list(self._undo),
            list(self._redo),
            list(self._pending),
        )
        self._depth += 1
        try:
            yield self
        except BaseException:
            self._depth -= 1
            (self._text, self._undo, self._redo, self._pending) = (
                snapshot[0],
                snapshot[1],
                snapshot[2],
                snapshot[3],
            )
            raise
        else:
            self._depth -= 1
            if self._depth == 0:
                self._flush_pending()
