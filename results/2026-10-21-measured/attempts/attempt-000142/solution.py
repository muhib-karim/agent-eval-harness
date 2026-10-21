class _Group:
    def __init__(self, buf):
        self._buf = buf
        self._start = 0

    def __enter__(self):
        buf = self._buf
        if buf._depth == 0:
            buf._current = []
        self._start = len(buf._current)
        buf._depth += 1
        return buf

    def __exit__(self, exc_type, exc, tb):
        buf = self._buf
        buf._depth -= 1
        if exc_type is not None:
            # roll back only this group's edits
            while len(buf._current) > self._start:
                op = buf._current.pop()
                buf._apply_inverse(op)
            if buf._depth == 0:
                buf._current = None
            return False
        if buf._depth == 0:
            ops = buf._current
            buf._current = None
            if ops:
                buf._undo.append(ops)
                buf._redo.clear()
        return False


class TextBuffer:
    def __init__(self, text: str = ""):
        if not isinstance(text, str):
            raise ValueError("text must be a str")
        self._text = text
        self._undo = []
        self._redo = []
        self._depth = 0
        self._current = None

    @property
    def text(self) -> str:
        return self._text

    @staticmethod
    def _is_int(x):
        return isinstance(x, int) and not isinstance(x, bool)

    def _apply(self, op):
        kind, idx, s = op
        if kind == 'i':
            self._text = self._text[:idx] + s + self._text[idx:]
        else:
            self._text = self._text[:idx] + self._text[idx + len(s):]

    def _apply_inverse(self, op):
        kind, idx, s = op
        self._apply(('d' if kind == 'i' else 'i', idx, s))

    def _record(self, op):
        self._apply(op)
        if self._depth > 0:
            self._current.append(op)
        else:
            self._undo.append([op])
            self._redo.clear()

    def insert(self, index: int, s: str) -> None:
        if not self._is_int(index) or not isinstance(s, str):
            raise ValueError("invalid arguments")
        if index < 0 or index > len(self._text):
            raise ValueError("index out of range")
        if s == "":
            return
        self._record(('i', index, s))

    def delete(self, start: int, end: int) -> None:
        if not self._is_int(start) or not self._is_int(end):
            raise ValueError("invalid arguments")
        if start < 0 or end < start or end > len(self._text):
            raise ValueError("range out of bounds")
        if start == end:
            return
        self._record(('d', start, self._text[start:end]))

    def undo(self) -> bool:
        if self._depth > 0:
            raise RuntimeError("cannot undo inside a group")
        if not self._undo:
            return False
        ops = self._undo.pop()
        for op in reversed(ops):
            self._apply_inverse(op)
        self._redo.append(ops)
        return True

    def redo(self) -> bool:
        if self._depth > 0:
            raise RuntimeError("cannot redo inside a group")
        if not self._redo:
            return False
        ops = self._redo.pop()
        for op in ops:
            self._apply(op)
        self._undo.append(ops)
        return True

    def group(self):
        return _Group(self)
