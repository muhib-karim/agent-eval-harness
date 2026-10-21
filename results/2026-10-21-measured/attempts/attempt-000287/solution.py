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

    def _position(self, value, name: str) -> None:
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"{name} must be an integer")

    def _record(self, edit) -> None:
        if self._groups:
            self._groups[-1].append(edit)
        else:
            self._undo.append([edit])
            self._redo.clear()

    def insert(self, index: int, s: str) -> None:
        self._position(index, "index")
        if not isinstance(s, str) or not 0 <= index <= len(self._text):
            raise ValueError("invalid insertion")
        if not s:
            return

        self._text = self._text[:index] + s + self._text[index:]
        self._record((index, "", s))

    def delete(self, start: int, end: int) -> None:
        self._position(start, "start")
        self._position(end, "end")
        if not 0 <= start <= end <= len(self._text):
            raise ValueError("invalid deletion")
        if start == end:
            return

        removed = self._text[start:end]
        self._text = self._text[:start] + self._text[end:]
        self._record((start, removed, ""))

    def _apply(self, edit, reverse: bool) -> None:
        index, removed, inserted = edit
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
        edits = self._undo.pop()
        for edit in reversed(edits):
            self._apply(edit, reverse=True)
        self._redo.append(edits)
        return True

    def redo(self) -> bool:
        if not self._redo:
            return False
        edits = self._redo.pop()
        for edit in edits:
            self._apply(edit, reverse=False)
        self._undo.append(edits)
        return True

    @contextmanager
    def group(self):
        edits = []
        self._groups.append(edits)
        try:
            yield self
        except BaseException:
            self._groups.pop()
            for edit in reversed(edits):
                self._apply(edit, reverse=True)
            raise
        else:
            self._groups.pop()
            if edits:
                if self._groups:
                    self._groups[-1].extend(edits)
                else:
                    self._undo.append(edits)
                    self._redo.clear()
