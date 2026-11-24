"""Menu scenes: Main Menu, Level Selection, Settings, How To Play."""
import colorsys
import math

import pygame

from .settings import WIDTH, HEIGHT, COLORS, TOTAL_LEVELS
from . import ui, sprites
from .background import Background, HUES
from .powerups import POWERUPS, POWERUP_ORDER


class MainMenu:
    def __init__(self, app):
        self.app = app
        self.bg = Background(0)
        self.t = 0.0
        a, s = app, app.save
        labels = [("Play Game", self.play, (60, 190, 110)),
                  ("Level Selection", lambda: a.goto(lambda: LevelSelect(a)), (70, 140, 255)),
                  ("Settings", lambda: a.goto(lambda: Settings(a)), (150, 100, 230)),
                  ("How to Play", lambda: a.goto(lambda: HowToPlay(a)), (230, 150, 50)),
                  ("Exit Game", a.quit, (200, 80, 90))]
        self.buttons = [ui.Button((510, 300 + i * 70, 260, 58), t, cb, col) for i, (t, cb, col) in enumerate(labels)]

    def play(self):
        from .gameplay import GameplayScene
        n = min(self.app.save.unlocked, TOTAL_LEVELS)
        self.app.goto(lambda: GameplayScene(self.app, n))

    def handle_event(self, e):
        for b in self.buttons:
            if b.handle_event(e):
                return

    def update(self, dt):
        self.t += dt
        self.bg.update(dt)
        for b in self.buttons:
            b.update(dt, self.app.mouse)

    def draw(self, surf):
        self.bg.draw(surf)
        for i, key in enumerate((0, 3, 5, 6)):
            side = -1 if i % 2 == 0 else 1
            x = WIDTH // 2 + side * (330 + (i // 2) * 120)
            y = 420 + math.sin(self.t * 1.5 + i) * 22 + (i // 2) * 60
            sprites.draw_ball(surf, key, x, y, rad=58)
        for line, cy, off in (("BUBBLE", 100, 0), ("SHOOTER", 190, 3)):
            f = ui.font(92)
            widths = [f.size(ch)[0] for ch in line]
            x = WIDTH // 2 - sum(widths) / 2
            for i, ch in enumerate(line):
                y = cy + math.sin(self.t * 3 + i * 0.6 + off) * 8
                ui.text(surf, ch, 92, COLORS[(i + off + int(self.t * 2)) % len(COLORS)], (x + widths[i] / 2, y))
                x += widths[i]
        for b in self.buttons:
            b.draw(surf)
        d = self.app.save.data
        ui.text(surf, "Total Score: %d     High Score: %d     Completed: %d/%d" % (
            d["total_score"], d["high_score"], len(d["completed"]), TOTAL_LEVELS), 22, (200, 215, 255),
            (WIDTH // 2, 676))


class LevelSelect:
    CELL_W, CELL_H, GAP, COLS_N = 92, 84, 8, 10

    def __init__(self, app):
        self.app = app
        self.bg = Background(2)
        self.save = app.save
        self.t = 0.0
        self.area = pygame.Rect(140, 120, 1000, 500)
        self.pitch = self.CELL_H + self.GAP
        self.total_h = (TOTAL_LEVELS // self.COLS_N) * self.pitch
        self.max_scroll = max(0, self.total_h - self.area.h)
        row = (min(self.save.unlocked, TOTAL_LEVELS) - 1) // self.COLS_N
        self.scroll = max(0, min(self.max_scroll, row * self.pitch - self.area.h // 2))
        self.back = ui.Button((40, 28, 150, 52), "Back", self.go_back, (200, 80, 90), 26)

    def go_back(self):
        self.app.goto(lambda: MainMenu(self.app))

    def _rect(self, n):
        i = n - 1
        x = self.area.x + (i % self.COLS_N) * (self.CELL_W + self.GAP)
        y = self.area.y + (i // self.COLS_N) * self.pitch - self.scroll
        return pygame.Rect(x, y, self.CELL_W, self.CELL_H)

    def handle_event(self, e):
        if self.back.handle_event(e):
            return
        if e.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, min(self.max_scroll, self.scroll - e.y * 60))
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                self.go_back()
            elif e.key in (pygame.K_DOWN, pygame.K_PAGEDOWN):
                self.scroll = min(self.max_scroll, self.scroll + 94)
            elif e.key in (pygame.K_UP, pygame.K_PAGEUP):
                self.scroll = max(0, self.scroll - 94)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.area.collidepoint(e.pos):
            for n in range(1, TOTAL_LEVELS + 1):
                if self._rect(n).collidepoint(e.pos):
                    if self.save.is_unlocked(n):
                        from .gameplay import GameplayScene
                        if self.app.audio:
                            self.app.audio.play("click")
                        self.app.goto(lambda n=n: GameplayScene(self.app, n))
                    else:
                        if self.app.audio:
                            self.app.audio.play("thud")
                    break
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button in (4, 5):
            pass

    def update(self, dt):
        self.t += dt
        self.bg.update(dt)
        self.back.update(dt, self.app.mouse)

    def draw(self, surf):
        self.bg.draw(surf)
        ui.text(surf, "SELECT LEVEL", 56, (255, 255, 255), (WIDTH // 2, 60))
        ui.text(surf, "Mouse wheel / arrow keys to scroll", 18, (190, 205, 245), (WIDTH // 2, 100))
        ui.panel(surf, self.area.inflate(24, 16), (8, 10, 30, 110), 18)
        old = surf.get_clip()
        surf.set_clip(self.area)
        mouse = self.app.mouse
        for n in range(1, TOTAL_LEVELS + 1):
            r = self._rect(n)
            if r.bottom < self.area.top or r.top > self.area.bottom:
                continue
            unlocked = self.save.is_unlocked(n)
            done = self.save.is_completed(n)
            hue = HUES[(n - 1) // 10]
            if not unlocked:
                top, bot = (70, 74, 96), (45, 48, 68)
            else:
                top = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(hue, 0.55, 0.95))
                bot = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(hue, 0.75, 0.65))
            hover = unlocked and r.collidepoint(mouse) and self.area.collidepoint(mouse)
            rr = r.inflate(8, 8) if hover else r
            surf.blit(ui.gradient_round(rr.w, rr.h, top, bot, 14), rr.topleft)
            current = unlocked and not done and n == self.save.unlocked
            border = (255, 255, 120) if current and int(self.t * 3) % 2 == 0 else (255, 255, 255)
            pygame.draw.rect(surf, border if unlocked else (110, 115, 140), rr, 2, border_radius=14)
            if unlocked:
                ui.text(surf, str(n), 30, (255, 255, 255), (rr.centerx, rr.y + 30))
                st = self.save.stars(n)
                for i in range(3):
                    ui.draw_star(surf, (rr.centerx - 22 + i * 22, rr.y + 62), 9, i < st)
            else:
                ui.draw_lock(surf, (rr.centerx, rr.y + 34), 26)
                ui.text(surf, str(n), 18, (170, 176, 200), (rr.centerx, rr.y + 66), shadow=False)
        surf.set_clip(old)
        # scrollbar
        if self.max_scroll > 0:
            bar = pygame.Rect(self.area.right + 20, self.area.y, 8, self.area.h)
            pygame.draw.rect(surf, (40, 46, 82), bar, border_radius=4)
            h = max(40, int(bar.h * self.area.h / self.total_h))
            y = bar.y + int((bar.h - h) * self.scroll / self.max_scroll)
            pygame.draw.rect(surf, (140, 170, 255), (bar.x, y, 8, h), border_radius=4)
        self.back.draw(surf)
        d = self.save.data
        ui.text(surf, "Completed %d/%d    Stars %d/%d" % (len(d["completed"]), TOTAL_LEVELS,
                sum(int(v) for v in d["stars"].values()), TOTAL_LEVELS * 3), 22, (220, 230, 255), (WIDTH // 2, 676))


class Settings:
    def __init__(self, app):
        self.app = app
        self.bg = Background(4)
        s = app.save.settings
        self.confirm_reset = False

        def setter(key, apply=True):
            def f(v):
                s[key] = v
                app.save.save()
                if apply:
                    app.audio.apply()
            return f
        self.widgets = [
            ui.Toggle((820, 200), s["music"], setter("music")),
            ui.Toggle((820, 270), s["sfx"], setter("sfx")),
            ui.Slider((700, 350, 240, 20), s["music_volume"], setter("music_volume")),
            ui.Slider((700, 420, 240, 20), s["sfx_volume"], setter("sfx_volume")),
            ui.Toggle((820, 490), s["fullscreen"], lambda v: app.set_fullscreen(v)),
        ]
        self.buttons = [
            ui.Button((470, 540, 340, 54), "Reset Progress", self.reset, (200, 80, 90), 24),
            ui.Button((510, 610, 260, 56), "Back", lambda: app.goto(lambda: MainMenu(app)), (70, 140, 255))]

    def reset(self):
        if not self.confirm_reset:
            self.confirm_reset = True
            self.buttons[0].label = "Click again to confirm"
        else:
            self.app.save.reset()
            self.confirm_reset = False
            self.buttons[0].label = "Progress reset!"

    def handle_event(self, e):
        for w in self.widgets + self.buttons:
            if w.handle_event(e):
                return
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self.app.goto(lambda: MainMenu(self.app))

    def update(self, dt):
        self.bg.update(dt)
        for w in self.widgets + self.buttons:
            w.update(dt, self.app.mouse)

    def draw(self, surf):
        self.bg.draw(surf)
        ui.text(surf, "SETTINGS", 60, (255, 255, 255), (WIDTH // 2, 80))
        ui.panel(surf, (400, 150, 480, 380), (8, 10, 30, 150), 22)
        for label, y in (("Music", 200), ("Sound Effects", 270), ("Music Volume", 350),
                         ("Effects Volume", 420), ("Fullscreen (F11)", 490)):
            ui.text(surf, label, 26, (235, 240, 255), (430, y), "midleft")
        for w in self.widgets:
            w.draw(surf)
        for b in self.buttons:
            b.draw(surf)


class HowToPlay:
    def __init__(self, app):
        self.app = app
        self.bg = Background(6)
        self.back = ui.Button((510, 648, 260, 52), "Back", lambda: app.goto(lambda: MainMenu(app)), (70, 140, 255))

    def handle_event(self, e):
        if self.back.handle_event(e):
            return
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self.app.goto(lambda: MainMenu(self.app))

    def update(self, dt):
        self.bg.update(dt)
        self.back.update(dt, self.app.mouse)

    def draw(self, surf):
        self.bg.draw(surf)
        ui.text(surf, "HOW TO PLAY", 54, (255, 255, 255), (WIDTH // 2, 50))
        ui.panel(surf, (60, 95, 560, 535), (8, 10, 30, 150), 20)
        lines = ["Move the mouse to aim - the dotted guide shows the path.",
                 "Left click to shoot. Bubbles bounce off the side walls.",
                 "Match 3 or more bubbles of the same colour to pop them.",
                 "Bubbles cut off from the ceiling fall down for bonus points.",
                 "Right click or Space swaps the loaded and the next bubble.",
                 "Gray stone bubbles cannot be matched - pop around them.",
                 "Clear every coloured bubble to win the level.",
                 "You lose if you run out of shots or the bubbles reach the",
                 "red dashed line at the bottom.",
                 "Stars: fewer shots = more stars (up to 3 per level).",
                 "Win levels to unlock new ones and earn power-ups.",
                 "P / Esc = pause,  R = restart,  1-6 = use power-ups."]
        for i, l in enumerate(lines):
            ui.text(surf, l, 20, (230, 236, 255), (86, 130 + i * 40), "midleft", bold=False)
        ui.panel(surf, (650, 95, 570, 535), (8, 10, 30, 150), 20)
        ui.text(surf, "POWER-UPS", 30, (255, 220, 120), (935, 125))
        for i, pid in enumerate(POWERUP_ORDER):
            y = 190 + i * 72
            sprites.draw_ball(surf, pid, 700, y, scale=1.2)
            info = POWERUPS[pid]
            ui.text(surf, info["name"], 24, (255, 255, 255), (745, y - 14), "midleft")
            ui.text(surf, info["desc"], 17, (200, 212, 245), (745, y + 12), "midleft", bold=False)
            ui.text(surf, "Level %d" % info["unlock"], 18, (255, 220, 120), (1195, y), "midright")
        self.back.draw(surf)
