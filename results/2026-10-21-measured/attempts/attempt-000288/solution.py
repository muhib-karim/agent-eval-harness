from contextlib import contextmanager


class TextBuffer:
    def __init__(self, text: str = ""):
        if not isinstance(text, str):
            raise ValueError("text must be a string")
        self._text = text
        self._undo = []
        self._redo = []
        self._groups = []

    @property
    def text(self) -> str:
        return self._text

    def _check_position(self, value: int) -> None:
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("position must be an integer")
        if not 0 <= value <= len(self._text):
            raise ValueError("position out of range")

    def _record(self, operation) -> None:
        self._redo.clear()
        if self._groups:
            self._groups[-1]["operations"].append(operation)
        else:
            self._undo.append((operation,))

    def insert(self, index: int, s: str) -> None:
        self._check_position(index)
        if not isinstance(s, str):
            raise ValueError("inserted value must be a string")
        if not s:
            return

        self._text = self._text[:index] + s + self._text[index:]
        self._record((index, "", s))

    def delete(self, start: int, end: int) -> None:
        self._check_position(start)
        self._check_position(end)
        if start > end:
            raise ValueError("start must not exceed end")
        if start == end:
            return

        removed = self._text[start:end]
        self._text = self._text[:start] + self._text[end:]
        self._record((start, removed, ""))

    def _apply(self, operation, reverse: bool = False) -> None:
        index, removed, inserted = operation
        if reverse:
            removed, inserted = inserted, removed
        self._text = (
            self._text[:index]
            + inserted
            + self._text[index + len(removed):]
        )

    def undo(self) -> bool:
        if not self._undo:
            return False
        operations = self._undo.pop()
        for operation in reversed(operations):
            self._apply(operation, reverse=True)
        self._redo.append(operations)
        return True

    def redo(self) -> bool:
        if not self._redo:
            return False
        operations = self._redo.pop()
        for operation in operations:
            self._apply(operation)
        self._undo.append(operations)
        return True

    @contextmanager
    def group(self):
        frame = {
            "operations": [],
            "text": self._text,
            "undo": self._undo.copy(),
            "redo": self._redo.copy(),
        }
        self._groups.append(frame)
        try:
            yield
        except BaseException:
            self._text = frame["text"]
            self._undo = frame["undo"]
            self._redo = frame["redo"]
            self._groups.pop()
            raise
        else:
            self._groups.pop()
            operations = frame["operations"]
            if operations:
                if self._groups:
                    self._groups[-1]["operations"].extend(operations)
                else:
                    self._undo.append(tuple(operations))
