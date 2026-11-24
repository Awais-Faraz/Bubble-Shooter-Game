"""Hex-grid logic, collision and projectile movement (pure Python, no pygame)."""
from .settings import R, D, H, COLS, MAX_ROWS, TOP, BOARD_LEFT, BOARD_RIGHT


class Grid:
    """Hexagonal bubble grid. Odd rows are shifted right by one radius."""

    def __init__(self):
        self.cells = [[None] * COLS for _ in range(MAX_ROWS)]
        self.version = 0          # bumps on every change (used to cache the aim guide)

    @staticmethod
    def center(r, c):
        x = BOARD_LEFT + R + c * D + (R if r % 2 else 0)
        y = TOP + R + r * H
        return x, y

    @staticmethod
    def neighbors(r, c):
        if r % 2 == 0:
            cand = ((r, c - 1), (r, c + 1), (r - 1, c - 1), (r - 1, c), (r + 1, c - 1), (r + 1, c))
        else:
            cand = ((r, c - 1), (r, c + 1), (r - 1, c), (r - 1, c + 1), (r + 1, c), (r + 1, c + 1))
        return [(a, b) for a, b in cand if 0 <= a < MAX_ROWS and 0 <= b < COLS]

    def remove(self, cells):
        """Remove the given (r,c) cells; returns list of (r,c,bubble) actually removed."""
        out = []
        for r, c in cells:
            b = self.cells[r][c]
            if b is not None:
                out.append((r, c, b))
                self.cells[r][c] = None
        self.version += 1
        return out

    def place(self, r, c, bubble):
        self.cells[r][c] = bubble
        self.version += 1

    def occupied(self):
        out = []
        for r in range(MAX_ROWS):
            for c in range(COLS):
                b = self.cells[r][c]
                if b is not None:
                    out.append((r, c, b))
        return out

    def count_colored(self):
        return sum(1 for row in self.cells for b in row if b is not None and b.kind == "normal")

    def has_empty_neighbor(self, r, c):
        return any(self.cells[a][b] is None for a, b in self.neighbors(r, c))

    def colors_present(self, exposed_only=False):
        out = set()
        for r in range(MAX_ROWS):
            for c in range(COLS):
                b = self.cells[r][c]
                if b is not None and b.kind == "normal":
                    if not exposed_only or self.has_empty_neighbor(r, c):
                        out.add(b.color)
        return out

    def find_group(self, r, c):
        """All connected normal bubbles with the same colour as (r,c)."""
        b = self.cells[r][c]
        if b is None or b.kind != "normal":
            return []
        col = b.color
        seen = {(r, c)}
        stack = [(r, c)]
        while stack:
            cr, cc = stack.pop()
            for a, bb in self.neighbors(cr, cc):
                if (a, bb) not in seen:
                    nb = self.cells[a][bb]
                    if nb is not None and nb.kind == "normal" and nb.color == col:
                        seen.add((a, bb))
                        stack.append((a, bb))
        return list(seen)

    def find_floating(self):
        """Cells not connected (through any bubble) to the ceiling row."""
        stack = [(0, c) for c in range(COLS) if self.cells[0][c] is not None]
        seen = set(stack)
        while stack:
            cr, cc = stack.pop()
            for a, bb in self.neighbors(cr, cc):
                if (a, bb) not in seen and self.cells[a][bb] is not None:
                    seen.add((a, bb))
                    stack.append((a, bb))
        return [(r, c) for r in range(MAX_ROWS) for c in range(COLS)
                if self.cells[r][c] is not None and (r, c) not in seen]

    def nearest_empty(self, x, y):
        """Empty cell (touching a bubble or the ceiling) closest to point (x,y)."""
        rr = int(round((y - TOP - R) / H))
        best, bd = None, 1e18
        for r in range(max(0, rr - 2), min(MAX_ROWS, rr + 3)):
            for c in range(COLS):
                if self.cells[r][c] is not None:
                    continue
                if r > 0 and not any(self.cells[a][b] is not None for a, b in self.neighbors(r, c)):
                    continue
                cx, cy = self.center(r, c)
                d = (cx - x) ** 2 + (cy - y) ** 2
                if d < bd:
                    bd, best = d, (r, c)
        if best is None:                      # fallback: scan everything
            for r in range(MAX_ROWS):
                for c in range(COLS):
                    if self.cells[r][c] is None and (r == 0 or any(
                            self.cells[a][b] is not None for a, b in self.neighbors(r, c))):
                        cx, cy = self.center(r, c)
                        d = (cx - x) ** 2 + (cy - y) ** 2
                        if d < bd:
                            bd, best = d, (r, c)
        return best

    def collides(self, x, y):
        """True if a bubble centred at (x,y) overlaps a grid bubble."""
        rr = int((y - TOP - R) / H + 0.5)
        c0 = int((x - BOARD_LEFT - R) / D)
        lim = (D * 0.9) ** 2
        for r in range(max(0, rr - 1), min(MAX_ROWS, rr + 2)):
            row = self.cells[r]
            for c in range(max(0, c0 - 2), min(COLS, c0 + 3)):
                if row[c] is not None:
                    cx, cy = self.center(r, c)
                    if (cx - x) ** 2 + (cy - y) ** 2 < lim:
                        return True
        return False


def match_and_fall(grid, r, c):
    """Pop the matching group at (r,c) if >=3, then drop floating bubbles.
    Returns (popped, fallen) as lists of (r,c,bubble)."""
    grp = grid.find_group(r, c)
    if len(grp) >= 3:
        popped = grid.remove(grp)
        fallen = grid.remove(grid.find_floating())
        return popped, fallen
    return [], []


def advance(grid, x, y, ux, uy, dist, stop=True):
    """Move a projectile `dist` pixels with wall bounces.
    Returns (x, y, ux, uy, hit). hit=True when it touches the ceiling or a bubble."""
    n = max(1, int(dist / 5.0 + 0.999))
    sd = dist / n
    left, right = BOARD_LEFT + R, BOARD_RIGHT - R
    for _ in range(n):
        x += ux * sd
        y += uy * sd
        if x < left:
            x, ux = 2 * left - x, -ux
        elif x > right:
            x, ux = 2 * right - x, -ux
        if y <= TOP + R:
            return x, TOP + R, ux, uy, True
        if stop and grid.collides(x, y):
            return x, y, ux, uy, True
    return x, y, ux, uy, False


def trace(grid, x, y, ux, uy, max_len=2200.0, gap=22.0, stop=True):
    """Predict the path for the aiming guide. Returns (dots, end_point_or_None)."""
    dots = []
    travelled, next_dot, step = 0.0, 0.0, 7.0
    while travelled < max_len:
        x, y, ux, uy, hit = advance(grid, x, y, ux, uy, step, stop)
        travelled += step
        if travelled >= next_dot:
            dots.append((x, y))
            next_dot += gap
        if hit:
            return dots, (x, y)
    return dots, None
