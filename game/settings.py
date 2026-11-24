"""Global constants and path helpers."""
import os
import sys

WIDTH, HEIGHT = 1280, 720
FPS = 60
TOTAL_LEVELS = 100

# ---- Board geometry (hex grid) ----
R = 22                       # bubble radius
D = R * 2                    # bubble diameter
H = D * 0.866                # row height
COLS = 13
MAX_ROWS = 18
LOSE_ROW = 14                # a bubble in this row (or lower) = game over
BOARD_W = COLS * D + R
BOARD_LEFT = (WIDTH - BOARD_W) // 2
BOARD_RIGHT = BOARD_LEFT + BOARD_W
TOP = 66
SHOOTER_X, SHOOTER_Y = WIDTH // 2, 664
BUBBLE_SPEED = 980.0

COLORS = [
    (235, 64, 82),    # red
    (255, 152, 38),   # orange
    (252, 220, 56),   # yellow
    (72, 205, 96),    # green
    (48, 204, 226),   # cyan
    (66, 110, 245),   # blue
    (164, 84, 226),   # purple
    (250, 112, 184),  # pink
]


def base_dir():
    """Folder of the project (or of the .exe when frozen by PyInstaller)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def data_path(name):
    """Path inside the data/ folder (created if missing)."""
    d = os.path.join(base_dir(), "data")
    try:
        os.makedirs(d, exist_ok=True)
    except OSError:
        pass
    return os.path.join(d, name)
