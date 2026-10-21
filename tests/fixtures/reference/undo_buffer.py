from contextlib import contextmanager


class TextBuffer:
    def __init__(self, text=""):
        if not isinstance(text, str):
            raise ValueError("text must be str")
        self._text = text
        self._undo = []
        self._redo = []
        self._group = None
        self._depth = 0

    @property
    def text(self):
        return self._text

    @staticmethod
    def _pos(value):
        if type(value) is not int:
            raise ValueError("positions must be int")
        return value

    def _apply(self, op):
        kind, index, s = op
        if kind == "insert":
            self._text = self._text[:index] + s + self._text[index:]
        else:
            self._text = self._text[:index] + self._text[index + len(s) :]

    @staticmethod
    def _inverse(op):
        kind, index, s = op
        return ("delete" if kind == "insert" else "insert", index, s)

    def _record(self, op):
        self._apply(op)
        if self._group is not None:
            self._group.append(op)
        else:
            self._undo.append([op])
            self._redo.clear()

    def insert(self, index, s):
        index = self._pos(index)
        if not isinstance(s, str) or not 0 <= index <= len(self._text):
            raise ValueError("invalid insert")
        if s:
            self._record(("insert", index, s))

    def delete(self, start, end):
        start, end = self._pos(start), self._pos(end)
        if not 0 <= start <= end <= len(self._text):
            raise ValueError("invalid range")
        if start != end:
            self._record(("delete", start, self._text[start:end]))

    def undo(self):
        if not self._undo:
            return False
        ops = self._undo.pop()
        for op in reversed(ops):
            self._apply(self._inverse(op))
        self._redo.append(ops)
        return True

    def redo(self):
        if not self._redo:
            return False
        ops = self._redo.pop()
        for op in ops:
            self._apply(op)
        self._undo.append(ops)
        return True

    @contextmanager
    def group(self):
        outer = self._depth == 0
        if outer:
            self._group = []
        self._depth += 1
        try:
            yield self
        except BaseException:
            self._depth -= 1
            if outer:
                for op in reversed(self._group):
                    self._apply(self._inverse(op))
                self._group = None
            raise
        self._depth -= 1
        if outer:
            ops, self._group = self._group, None
            if ops:
                self._undo.append(ops)
                self._redo.clear()
