"""Bubble data object (no graphics here - see sprites.py)."""


class Bubble:
    """A bubble stored in the grid. kind: 'normal' (coloured) or 'stone' (obstacle)."""
    __slots__ = ("color", "kind")

    def __init__(self, color=0, kind="normal"):
        self.color = color
        self.kind = kind

    @property
    def key(self):
        """Sprite key: colour index for normal bubbles, 'stone' for obstacles."""
        return self.color if self.kind == "normal" else "stone"
