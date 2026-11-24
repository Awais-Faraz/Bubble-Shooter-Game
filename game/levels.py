"""Procedural generation of the 100 levels (deterministic) + fair shot limits.

Every level is generated from its number, then a simple "bot" plays it to
measure a par (best-effort shot count). The shot limit is always larger than
what the bot needs, so every level is completable.
"""
import math
import random

from .settings import COLS, LOSE_ROW
from .bubble import Bubble
from .physics import Grid, match_and_fall

TIER_NAMES = ["Very Easy", "Easy", "Normal", "Medium", "Medium-Hard",
              "Hard", "Very Hard", "Expert", "Extremely Difficult", "Master Challenge"]


def tier_name(n):
    return TIER_NAMES[(n - 1) // 10]


# ---------------------------------------------------------------- patterns
def _centered(c, w):
    m = (COLS - w) // 2
    return m <= c < m + w


def _p_classic(r, c, rows): return True
def _p_pyramid(r, c, rows): return _centered(c, max(3, COLS - int(r * (COLS - 3) / max(1, rows - 1))))


def _p_diamond(r, c, rows):
    mid = max(1.0, (rows - 1) / 2)
    return _centered(c, 3 + int((COLS - 3) * (1 - abs(r - mid) / mid)))


def _p_hourglass(r, c, rows):
    mid = max(1.0, (rows - 1) / 2)
    return _centered(c, 3 + int((COLS - 3) * abs(r - mid) / mid))


def _p_zigzag(r, c, rows):
    shift = (COLS - 8) // 2 + int(round(2 * math.sin(r * 0.9)))
    return shift <= c < shift + 8


def _p_swiss(r, c, rows): return r == 0 or (r * 5 + c * 3) % 6 != 0
def _p_pillars(r, c, rows): return r < 2 or c % 4 != 3
def _p_waves(r, c, rows): return _centered(c, 7 + int(5 * abs(math.sin(r * 0.7))))
def _p_fortress(r, c, rows): return not (rows >= 5 and 2 <= r <= rows - 2 and 4 <= c <= 8)
def _p_towers(r, c, rows): return r < 2 or c < 4 or c > 8
def _p_stairs(r, c, rows): return c < min(COLS, 4 + 2 * r)


PATTERNS = [("Classic", _p_classic), ("Pyramid", _p_pyramid), ("Diamond", _p_diamond),
            ("Hourglass", _p_hourglass), ("Zigzag", _p_zigzag), ("Swiss Cheese", _p_swiss),
            ("Pillars", _p_pillars), ("Waves", _p_waves), ("Fortress", _p_fortress),
            ("Twin Towers", _p_towers), ("Staircase", _p_stairs)]
POOLS = [[0, 1, 2], [0, 1, 2, 4, 10], [0, 1, 2, 3, 4, 5, 7, 10], list(range(11))]


def _pool_for(tier):
    return POOLS[0 if tier == 0 else 1 if tier == 1 else 2 if tier <= 3 else 3]


# ---------------------------------------------------------------- bot
def simulate(cells, seed=1, sloppy=0.0, limit=500):
    """Play the level with a logic-only bot; returns number of shots used."""
    g = Grid()
    for r, c, col, kind in cells:
        g.cells[r][c] = Bubble(col, kind)
    rng = random.Random(seed)
    used = 0
    while g.count_colored() > 0 and used < limit:
        pool = sorted(g.colors_present(True) or g.colors_present())
        color = rng.choice(pool)
        options = []
        for r in range(LOSE_ROW):
            for c in range(COLS):
                if g.cells[r][c] is not None:
                    continue
                if r > 0 and not any(g.cells[a][b] is not None for a, b in Grid.neighbors(r, c)):
                    continue
                g.cells[r][c] = Bubble(color)
                grp = g.find_group(r, c)
                if len(grp) >= 3:
                    removed = g.remove(grp)
                    fl = g.find_floating()
                    gain = 100 + len(grp) * 3 + len(fl) * 4
                    for rr, cc, b in removed:
                        g.cells[rr][cc] = b
                else:
                    gain = len(grp) * 5 - r * 0.1
                g.cells[r][c] = None
                options.append((gain, r, c))
        if not options:
            break
        options.sort(reverse=True)
        if sloppy and rng.random() < sloppy:
            gain, r, c = rng.choice(options[:3])
        else:
            gain, r, c = options[0]
        g.cells[r][c] = Bubble(color)
        match_and_fall(g, r, c)
        used += 1
    return used


def compute_par(cells):
    """Returns (par, worst): average and worst shot count of 6 bot runs."""
    vals = [simulate(cells, s) for s in (1, 2, 3, 4, 5, 6)]
    return max(1, int(math.ceil(sum(vals) / 6.0))), max(vals)


# ---------------------------------------------------------------- level object
class Level:
    def __init__(self):
        self.number = 0
        self.tier = 0
        self.tier_name = ""
        self.name = ""
        self.boss = False
        self.colors = []
        self.cells = []          # (row, col, colour_index, kind)
        self.rows = 0
        self.shots = None        # None = unlimited
        self.par = 1
        self.worst = 1
        self.t3 = 1              # max shots for 3 stars
        self.t2 = 1              # max shots for 2 stars

    def stars_for(self, used):
        if used <= self.t3:
            return 3
        if used <= self.t2:
            return 2
        return 1


def _generate(n):
    rng = random.Random(7919 * n + 13)
    tier = (n - 1) // 10
    boss = (n % 10 == 0)
    ncol = [3, 4, 4, 5, 5, 6, 6, 7, 7, 8][tier]
    if boss:
        ncol = min(8, ncol + 1)
    rows = min(11, 3 + int(n * 0.08))
    if boss:
        rows = min(11, rows + 1)
    pool = _pool_for(tier)
    pidx = 0 if n <= 3 else pool[(n * 5 + tier * 3 + n // 7) % len(pool)]
    pname, pf = PATTERNS[pidx]
    window = min(COLS, 7 + n // 2) if n < 12 else COLS
    palette = rng.sample(range(8), ncol)
    p_cluster = max(0.22, 0.6 - n * 0.0038)

    mask = [(r, c) for r in range(rows) for c in range(COLS)
            if pf(r, c, rows) and _centered(c, window)]
    cmap = {}
    for r, c in mask:
        cand = [cmap[nb] for nb in Grid.neighbors(r, c) if nb in cmap]
        if cand and rng.random() < p_cluster:
            cmap[(r, c)] = rng.choice(cand)
        else:
            cmap[(r, c)] = rng.choice(palette)

    frac = 0.0 if n < 31 else min(0.13, (n - 30) * 0.0017)
    if boss and n >= 20:
        frac = max(frac, 0.05) + 0.03
    keys = [k for k in cmap if k[0] >= 1]
    rng.shuffle(keys)
    stones = set(keys[:int(len(keys) * frac)])

    g = Grid()
    for (r, c), col in cmap.items():
        g.cells[r][c] = Bubble(col, "stone" if (r, c) in stones else "normal")
    g.remove(g.find_floating())            # nothing may start floating
    cells = [(r, c, b.color, b.kind) for r, c, b in g.occupied()]
    return tier, boss, palette, rows, pname, cells


_CACHE = {}


def build_level(n):
    if n in _CACHE:
        return _CACHE[n]
    tier, boss, palette, rows, pname, cells = _generate(n)
    lv = Level()
    lv.number, lv.tier, lv.tier_name, lv.boss = n, tier, tier_name(n), boss
    lv.colors, lv.rows, lv.cells = palette, rows, cells
    lv.name = ("Boss: " if boss else "") + pname
    try:
        from .level_pars import PARS
        pair = PARS.get(n) or compute_par(cells)
    except ImportError:
        pair = compute_par(cells)
    lv.par, lv.worst = pair
    lv.t3 = int(lv.par * 1.3) + 1
    if n <= 5:
        lv.shots = None
        lv.t2 = int(lv.par * 1.8) + 2
    else:
        slack = 1.8 - 0.4 * n / 100.0 - (0.1 if boss else 0.0)
        lv.shots = int(math.ceil(lv.worst * slack)) + 3
        lv.t2 = max(lv.t3, (lv.t3 + lv.shots) // 2)
    _CACHE[n] = lv
    return lv
