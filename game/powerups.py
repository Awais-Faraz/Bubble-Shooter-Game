"""Power-up definitions and their board effects (pure logic)."""
from .settings import R, D, COLS, MAX_ROWS
from .bubble import Bubble

POWERUP_ORDER = ["bomb", "rainbow", "lightning", "extra", "fire", "slow"]
POWERUPS = {
    "bomb":      {"name": "Bomb",      "desc": "Explodes nearby bubbles",       "unlock": 5},
    "rainbow":   {"name": "Rainbow",   "desc": "Matches any bubble colour",     "unlock": 10},
    "lightning": {"name": "Lightning", "desc": "Clears a complete row",         "unlock": 20},
    "extra":     {"name": "+5 Shots",  "desc": "Gives 5 additional moves",      "unlock": 30},
    "fire":      {"name": "Fire",      "desc": "Burns through bubbles in path", "unlock": 40},
    "slow":      {"name": "Slow-Mo",   "desc": "Slows the game for 8 seconds",  "unlock": 50},
}


def apply_bomb(grid, r, c):
    """Remove every bubble near cell (r,c). Returns removed [(r,c,bubble)]."""
    cx, cy = grid.center(r, c)
    lim = (D * 1.8) ** 2 + 1
    cells = []
    for a in range(max(0, r - 3), min(MAX_ROWS, r + 4)):
        for b in range(COLS):
            if grid.cells[a][b] is not None:
                x, y = grid.center(a, b)
                if (x - cx) ** 2 + (y - cy) ** 2 <= lim:
                    cells.append((a, b))
    return grid.remove(cells)


def apply_lightning(grid, r):
    """Clear the whole row r."""
    return grid.remove([(r, c) for c in range(COLS) if grid.cells[r][c] is not None])


def rainbow_color(grid, r, c, rng):
    """Pick the colour that gives the biggest match at empty cell (r,c)."""
    best, best_n = None, 0
    for a, b in grid.neighbors(r, c):
        nb = grid.cells[a][b]
        if nb is not None and nb.kind == "normal":
            grid.cells[r][c] = Bubble(nb.color)
            n = len(grid.find_group(r, c))
            grid.cells[r][c] = None
            if n > best_n:
                best, best_n = nb.color, n
    if best is None:
        pool = sorted(grid.colors_present()) or [0]
        best = rng.choice(pool)
    return best


def fire_hits(grid, x, y):
    """Cells whose bubbles overlap the fireball at (x,y)."""
    lim = (R * 1.9) ** 2
    out = []
    for r in range(MAX_ROWS):
        for c in range(COLS):
            if grid.cells[r][c] is not None:
                cx, cy = grid.center(r, c)
                if abs(cy - y) < D and (cx - x) ** 2 + (cy - y) ** 2 < lim:
                    out.append((r, c))
    return out
