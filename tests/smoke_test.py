"""Smoke test of gameplay/menus. Uses the real pygame when installed
(headless SDL dummy drivers), otherwise a light stub so the logic still runs."""
import os, sys, random, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

try:
    import pygame
    REAL = True
except ImportError:
    REAL = False
    from unittest.mock import MagicMock
    class Rect:
        def __init__(s, *a):
            if len(a) == 1: a = (a[0].x, a[0].y, a[0].w, a[0].h) if isinstance(a[0], Rect) else tuple(a[0])
            s.x, s.y, s.w, s.h = a
        @property
        def center(s): return (s.x + s.w // 2, s.y + s.h // 2)
        @center.setter
        def center(s, v): s.x, s.y = v[0] - s.w // 2, v[1] - s.h // 2
        right = property(lambda s: s.x + s.w); bottom = property(lambda s: s.y + s.h)
        top = property(lambda s: s.y); centerx = property(lambda s: s.x + s.w // 2)
        centery = property(lambda s: s.y + s.h // 2); topleft = property(lambda s: (s.x, s.y))
        def collidepoint(s, *p):
            p = p[0] if len(p) == 1 else p
            return s.x <= p[0] < s.x + s.w and s.y <= p[1] < s.y + s.h
        def inflate(s, a, b): return Rect(s.x - a // 2, s.y - b // 2, s.w + a, s.h + b)
        def move(s, a, b): return Rect(s.x + a, s.y + b, s.w, s.h)
    pygame = MagicMock()
    pygame.Rect = Rect
    for i, n in enumerate("QUIT KEYDOWN MOUSEMOTION MOUSEBUTTONDOWN MOUSEBUTTONUP MOUSEWHEEL".split()):
        setattr(pygame, n, 100 + i)
    for i, n in enumerate("K_ESCAPE K_p K_SPACE K_r K_1 K_6 K_F11 K_DOWN K_UP K_PAGEDOWN K_PAGEUP".split()):
        setattr(pygame, n, 200 + i)
    sys.modules["pygame"] = pygame

from game.save_system import SaveSystem
from game.settings import *
from game import ui

class FakeApp:
    def __init__(self):
        self.save = SaveSystem(os.path.join(tempfile.mkdtemp(), "p.json"))
        self.audio = type("A", (), {"play": lambda s, n: None, "apply": lambda s: None})()
        self.mouse = (640, 100); self.went = None
    def goto(self, f): self.went = f
    def quit(self): pass
    def set_fullscreen(self, f): pass

def ev(t, **k):
    if REAL: return pygame.event.Event(t, **k)
    return type("E", (), dict(type=t, **k))()

def play(level, frames=1500, seed=1):
    from game.gameplay import GameplayScene
    app = FakeApp()
    app.save.data["unlocked"] = 100
    sc = GameplayScene(app, level)
    surf = pygame.Surface((WIDTH, HEIGHT)) if REAL else MagicMock()
    rnd = random.Random(seed)
    for f in range(frames):
        if sc.state == "play" and sc.proj is None and f % 5 == 0:
            for pid in ("bomb", "rainbow", "lightning", "fire", "extra", "slow"):
                app.save.data["inventory"][pid] = 3
            if rnd.random() < 0.2:
                sc.use_powerup(rnd.choice(["bomb", "rainbow", "lightning", "fire", "extra", "slow"]))
            app.mouse = (rnd.randint(BOARD_LEFT, BOARD_RIGHT), rnd.randint(80, 500))
            sc.handle_event(ev(pygame.MOUSEBUTTONDOWN, button=1, pos=app.mouse))
        sc.update(1 / 60)
        sc.draw(surf)
        if not REAL:
            surf.reset_mock(); pygame.reset_mock()
        if sc.state in ("won", "lost") and sc.end_delay <= 0 and f > 10:
            break
    return sc.state

def main():
    print("real pygame" if REAL else "stub pygame (pygame not installed here)")
    states = {}
    for lv in (1, 6, 25, 45, 60, 100):
        for seed in range(3):
            st = play(lv, seed=seed)
            states[st] = states.get(st, 0) + 1
    print("gameplay results:", states)
    # force win + lose paths and the save system
    from game.gameplay import GameplayScene
    app = FakeApp()
    sc = GameplayScene(app, 1)
    for r in range(MAX_ROWS):
        for c in range(COLS): sc.grid.cells[r][c] = None
    sc._after_shot(); assert sc.state == "won"
    assert app.save.is_completed(1) and app.save.unlocked == 2 and app.save.stars(1) >= 1
    sc2 = FakeApp(); sc2 = GameplayScene(app, 2); sc2._lose("test"); assert sc2.state == "lost"
    sc.update(2.0); sc.update(0.1)
    surf = pygame.Surface((WIDTH, HEIGHT)) if REAL else MagicMock()
    sc.draw(surf); sc2.update(2.0); sc2.draw(surf)
    # save reload
    again = SaveSystem(app.save.path)
    assert again.unlocked == 2 and again.is_completed(1), "progress not persisted"
    # menus
    from game.scenes import MainMenu, LevelSelect, Settings, HowToPlay
    for cls in (MainMenu, LevelSelect, Settings, HowToPlay):
        s = cls(app); s.update(0.016); s.draw(surf)
    print("SMOKE TEST OK")

if __name__ == "__main__":
    main()
