"""Gameplay scene: in-level logic, rendering, pause / victory / game-over overlays."""
import math
import random

import pygame

from .settings import (WIDTH, HEIGHT, R, D, H, COLS, MAX_ROWS, LOSE_ROW, TOP, BOARD_LEFT, BOARD_RIGHT,
                       BOARD_W, SHOOTER_X, SHOOTER_Y, BUBBLE_SPEED, COLORS, TOTAL_LEVELS)
from . import ui, sprites
from .physics import Grid, advance, trace, match_and_fall
from .levels import build_level
from .shooter import Shooter, Shot, Projectile
from .effects import Effects
from .background import Background
from .player import Player
from .powerups import POWERUPS, POWERUP_ORDER, apply_bomb, apply_lightning, rainbow_color, fire_hits
from .bubble import Bubble

STONE_RGB = (150, 155, 170)


class GameplayScene:
    def __init__(self, app, level_no):
        self.app, self.n = app, level_no
        self.save, self.audio = app.save, app.audio
        self.player = Player(self.save)
        self.level = build_level(level_no)
        self.grid = Grid()
        for r, c, col, kind in self.level.cells:
            self.grid.cells[r][c] = Bubble(col, kind)
        self.initial = max(1, self.grid.count_colored())
        self.rng = random.Random()
        self.bg = Background(self.level.tier)
        self.fx = Effects()
        self.shooter = Shooter()
        self.score = 0
        self.shots_used = 0
        self.shots_left = self.level.shots
        self.state = "play"             # play / paused / won / lost
        self.proj = None
        self.slow = 0.0
        self.time = 0.0
        self.banner = 2.0
        self.pop_in = {}
        self.toasts = []
        self.overlay_t = 0.0
        self.end_delay = 0.0
        self.stars = 0
        self.new_best = False
        self.reason = ""
        self.reward = []
        self.confetti_t = 0.0
        self._guide_key = None
        self._guide = ([], None)
        self.pause_buttons, self.end_buttons = [], []
        self.top_buttons = [
            ui.Button((975, 22, 130, 46), "Restart", self.restart, (90, 120, 200), 22),
            ui.Button((1120, 22, 130, 46), "Pause", self.pause, (90, 120, 200), 22)]
        self.pb_rects = [pygame.Rect(975 + (i % 2) * 150, 150 + (i // 2) * 112, 140, 102) for i in range(6)]
        for pid in self.player.grant_unlocks(level_no):
            self.toast("New power-up unlocked: %s (+2)" % POWERUPS[pid]["name"])
        self.current = self._new_shot()
        self.next = self._new_shot()

    # ------------------------------------------------------------ helpers
    def toast(self, msg):
        self.toasts.append([msg, 2.2])

    def restart(self):
        self.app.goto(lambda: GameplayScene(self.app, self.n))

    def to_menu(self):
        from .scenes import MainMenu
        self.app.goto(lambda: MainMenu(self.app))

    def next_level(self):
        n = min(TOTAL_LEVELS, self.n + 1)
        self.app.goto(lambda: GameplayScene(self.app, n))

    def pause(self):
        if self.state == "play":
            self.state = "paused"
            self.pause_buttons = [
                ui.Button((510, 260, 260, 58), "Resume", self.resume, (60, 190, 110)),
                ui.Button((510, 332, 260, 58), "Restart", self.restart, (230, 150, 50)),
                ui.Button((510, 404, 260, 58), "Main Menu", self.to_menu, (200, 80, 90))]

    def resume(self):
        if self.state == "paused":
            self.state = "play"

    def _new_shot(self):
        pool = self.grid.colors_present(True) or self.grid.colors_present() or {0}
        return Shot("normal", self.rng.choice(sorted(pool)))

    def _refresh_queue(self):
        present = self.grid.colors_present()
        if present:
            if self.current.kind == "normal" and self.current.color not in present:
                self.current = self._new_shot()
            if self.next.kind == "normal" and self.next.color not in present:
                self.next = self._new_shot()

    # ------------------------------------------------------------ actions
    def shoot(self):
        if self.state != "play" or self.proj is not None:
            return
        if self.shots_left is not None and self.shots_left <= 0:
            return
        ux, uy = self.shooter.direction()
        self.proj = Projectile(self.current, ux, uy)
        self.shots_used += 1
        if self.shots_left is not None:
            self.shots_left -= 1
        self.shooter.recoil = 1.0
        self.audio.play("shoot")
        self.current, self.next = self.next, self._new_shot()

    def swap(self):
        if self.state == "play" and self.proj is None and self.current.kind == "normal" \
                and self.next.kind == "normal":
            self.current, self.next = self.next, self.current
            self.audio.play("click")

    def use_powerup(self, pid):
        if self.state != "play" or self.proj is not None:
            return
        info = POWERUPS[pid]
        if self.n < info["unlock"]:
            self.toast("%s unlocks at level %d" % (info["name"], info["unlock"]))
            return
        if self.player.count(pid) <= 0:
            self.toast("No %s left - win levels to earn more!" % info["name"])
            return
        if pid in ("bomb", "rainbow", "lightning", "fire"):
            if self.current.kind != "normal":
                self.toast("A power-up is already loaded")
                return
            self.player.use(pid)
            self.current = Shot(pid)
        elif pid == "extra":
            if self.shots_left is None:
                self.toast("This level has unlimited shots")
                return
            self.player.use(pid)
            self.shots_left += 5
            self.toast("+5 shots!")
        elif pid == "slow":
            if self.slow > 0:
                return
            self.player.use(pid)
            self.slow = 8.0
            self.toast("Slow motion!")
        self.audio.play("power")

    # ------------------------------------------------------------ update
    def update(self, dt):
        self.time += dt
        self.bg.update(dt)
        mouse = self.app.mouse
        for b in self.top_buttons + self.pause_buttons + self.end_buttons:
            b.update(dt, mouse)
        for t in self.toasts:
            t[1] -= dt
        self.toasts = [t for t in self.toasts if t[1] > 0]
        if self.state == "paused":
            return
        self.banner = max(0.0, self.banner - dt)
        gdt = dt * (0.4 if self.slow > 0 else 1.0)
        self.slow = max(0.0, self.slow - dt)
        self.fx.update(gdt)
        self.shooter.update(dt)
        for k in list(self.pop_in):
            self.pop_in[k] -= dt
            if self.pop_in[k] <= 0:
                del self.pop_in[k]
        if self.state == "play":
            self.shooter.aim(*mouse)
            if self.proj is not None:
                self._update_projectile(gdt)
        else:
            if self.state == "won":
                self.confetti_t += dt
                if self.confetti_t > 0.25:
                    self.confetti_t = 0.0
                    self.fx.confetti(8)
            if self.end_delay > 0:
                self.end_delay -= dt
                if self.end_delay <= 0:
                    self._build_end_buttons()
            else:
                self.overlay_t += dt

    def _update_projectile(self, dt):
        p = self.proj
        dist = BUBBLE_SPEED * dt
        was_right = p.ux > 0
        fire = p.kind == "fire"
        p.x, p.y, p.ux, p.uy, hit = advance(self.grid, p.x, p.y, p.ux, p.uy, dist, stop=not fire)
        p.travel += dist
        p.trail.append((p.x, p.y))
        if len(p.trail) > 9:
            p.trail.pop(0)
        if (p.ux > 0) != was_right:
            self.audio.play("bounce")
        if fire:
            removed = self.grid.remove(fire_hits(self.grid, p.x, p.y))
            if removed:
                self.fx.explosion(p.x, p.y, big=False)
                self._score_removed(removed, [], "fire")
            if hit or p.travel > 2800:
                self.proj = None
                fallen = self.grid.remove(self.grid.find_floating())
                self._score_removed([], fallen)
                self._after_shot()
        elif hit:
            self._land()

    def _land(self):
        p, self.proj = self.proj, None
        cell = self.grid.nearest_empty(p.x, p.y)
        if cell is None:
            self._lose("No room left on the board!")
            return
        r, c = cell
        popped, fallen, special = [], [], None
        if p.kind in ("normal", "rainbow"):
            color = p.color if p.kind == "normal" else rainbow_color(self.grid, r, c, self.rng)
            self.grid.place(r, c, Bubble(color))
            popped, fallen = match_and_fall(self.grid, r, c)
            if not popped:
                self.audio.play("thud")
                self.pop_in[(r, c)] = 0.18
                x, y = self.grid.center(r, c)
                self.fx.rings.append([x, y, 8, 30, 0.0, 0.25, COLORS[color]])
        elif p.kind == "bomb":
            x, y = self.grid.center(r, c)
            popped = apply_bomb(self.grid, r, c)
            fallen = self.grid.remove(self.grid.find_floating())
            self.fx.explosion(x, y)
            self.audio.play("bomb")
            special = "bomb"
        elif p.kind == "lightning":
            popped = apply_lightning(self.grid, r)
            fallen = self.grid.remove(self.grid.find_floating())
            self.fx.lightning_row(self.grid.center(r, 0)[1])
            self.audio.play("power")
            special = "lightning"
        self._score_removed(popped, fallen, special)
        self._after_shot()

    def _score_removed(self, popped, fallen, special=None):
        gain = 0
        if popped:
            n = len(popped)
            gain += n * 15 if special else n * 10 + (n - 3) * 10
            for r, c, b in popped:
                x, y = self.grid.center(r, c)
                self.fx.pop(x, y, COLORS[b.color] if b.kind == "normal" else STONE_RGB)
            if not special:
                self.audio.play("pop")
        for i, (r, c, b) in enumerate(fallen):
            x, y = self.grid.center(r, c)
            gain += 20 * (1 + i // 3)
            self.fx.fall(b.key, x, y)
        if fallen:
            self.audio.play("fall")
        if gain:
            self.score += gain
            src = popped or fallen
            r, c, _ = src[0]
            x, y = self.grid.center(r, c)
            self.fx.text("+%d" % gain, x, y - 10, (255, 240, 120), 28 if gain < 150 else 36)

    def _after_shot(self):
        if self.grid.count_colored() == 0:
            self._win()
            return
        if any(self.grid.cells[r][c] is not None for r in range(LOSE_ROW, MAX_ROWS) for c in range(COLS)):
            self._lose("The bubbles reached the bottom!")
            return
        if self.shots_left is not None and self.shots_left <= 0:
            self._lose("You ran out of shots!")
            return
        self._refresh_queue()

    def _win(self):
        self.state = "won"
        self.end_delay = 1.0
        if self.shots_left:
            self.score += self.shots_left * 50
        self.stars = self.level.stars_for(self.shots_used)
        self.new_best = self.save.complete_level(self.n, self.score, self.stars)
        self.reward = self.player.reward_random(self.n)
        self.audio.play("win")
        self.fx.confetti(90)

    def _lose(self, reason):
        self.state = "lost"
        self.reason = reason
        self.end_delay = 0.9
        self.audio.play("lose")

    def _build_end_buttons(self):
        if self.state == "won":
            self.end_buttons = []
            y = 400
            if self.n < TOTAL_LEVELS:
                self.end_buttons.append(ui.Button((510, y, 260, 54), "Next Level", self.next_level, (60, 190, 110)))
                y += 64
            self.end_buttons.append(ui.Button((510, y, 260, 54), "Replay", self.restart, (230, 150, 50)))
            self.end_buttons.append(ui.Button((510, y + 64, 260, 54), "Main Menu", self.to_menu, (200, 80, 90)))
        else:
            self.end_buttons = [
                ui.Button((510, 400, 260, 56), "Retry", self.restart, (60, 190, 110)),
                ui.Button((510, 470, 260, 56), "Main Menu", self.to_menu, (200, 80, 90))]

    # ------------------------------------------------------------ events
    def handle_event(self, e):
        if self.state == "paused":
            for b in self.pause_buttons:
                if b.handle_event(e):
                    return
            if e.type == pygame.KEYDOWN and e.key in (pygame.K_ESCAPE, pygame.K_p):
                self.resume()
            return
        if self.state in ("won", "lost"):
            for b in self.end_buttons:
                if b.handle_event(e):
                    return
            return
        for b in self.top_buttons:
            if b.handle_event(e):
                return
        if e.type == pygame.MOUSEBUTTONDOWN:
            if e.button == 1:
                for i, rect in enumerate(self.pb_rects):
                    if rect.collidepoint(e.pos):
                        self.use_powerup(POWERUP_ORDER[i])
                        return
                self.shooter.aim(*e.pos)
                self.shoot()
            elif e.button == 3:
                self.swap()
        elif e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_ESCAPE, pygame.K_p):
                self.pause()
            elif e.key == pygame.K_SPACE:
                self.swap()
            elif e.key == pygame.K_r:
                self.restart()
            elif pygame.K_1 <= e.key <= pygame.K_6:
                self.use_powerup(POWERUP_ORDER[e.key - pygame.K_1])

    # ------------------------------------------------------------ drawing
    def draw(self, surf):
        self.bg.draw(surf)
        self._draw_board(surf)
        self._draw_guide(surf)
        self.shooter.draw(surf, self.current, self.next)
        if self.proj is not None:
            self._draw_projectile(surf)
        self.fx.draw(surf)
        self._draw_hud(surf)
        if self.fx.shake > 0.5:
            snap = surf.copy()
            surf.blit(snap, (random.uniform(-1, 1) * self.fx.shake, random.uniform(-1, 1) * self.fx.shake))
        if self.slow > 0:
            ui.panel(surf, (0, 0, WIDTH, HEIGHT), (60, 120, 255, 28), 0, None)
        self._draw_toasts(surf)
        if self.banner > 0 and self.state == "play":
            a = int(255 * min(1.0, self.banner))
            ui.text(surf, "LEVEL %d" % self.n, 80, (255, 255, 255), (WIDTH // 2, 300), alpha=a)
            ui.text(surf, self.level.name, 34, (255, 220, 120), (WIDTH // 2, 365), alpha=a)
        if self.state == "paused":
            ui.dim(surf, 160)
            ui.panel(surf, (470, 170, 340, 320), (14, 18, 46, 235), 24)
            ui.text(surf, "PAUSED", 56, (255, 255, 255), (WIDTH // 2, 215))
            for b in self.pause_buttons:
                b.draw(surf)
        elif self.state in ("won", "lost") and self.end_delay <= 0:
            self._draw_end(surf)

    def _draw_board(self, surf):
        ui.panel(surf, (BOARD_LEFT - 14, TOP - 14, BOARD_W + 28, HEIGHT - TOP + 4), (8, 10, 30, 120), 16)
        pygame.draw.line(surf, (120, 160, 255), (BOARD_LEFT - 6, TOP - 6), (BOARD_LEFT - 6, HEIGHT - 12), 3)
        pygame.draw.line(surf, (120, 160, 255), (BOARD_RIGHT + 6, TOP - 6), (BOARD_RIGHT + 6, HEIGHT - 12), 3)
        pygame.draw.line(surf, (120, 160, 255), (BOARD_LEFT - 6, TOP - 6), (BOARD_RIGHT + 6, TOP - 6), 3)
        # danger line (dashed)
        y = int(TOP + LOSE_ROW * H)
        low = any(self.grid.cells[r][c] is not None for r in range(LOSE_ROW - 2, LOSE_ROW) for c in range(COLS))
        col = (255, 70, 70) if (low and int(self.time * 4) % 2 == 0) else (200, 60, 70)
        for x in range(BOARD_LEFT, BOARD_RIGHT, 24):
            pygame.draw.line(surf, col, (x, y), (x + 12, y), 2)
        for r in range(MAX_ROWS):
            row = self.grid.cells[r]
            for c in range(COLS):
                b = row[c]
                if b is not None:
                    x, y = self.grid.center(r, c)
                    t = self.pop_in.get((r, c))
                    sprites.draw_ball(surf, b.key, x, y, 1.0 + (t * 1.2 if t else 0.0))

    def _draw_guide(self, surf):
        if self.state != "play" or self.proj is not None:
            return
        fire = self.current.kind == "fire"
        key = (round(self.shooter.angle, 3), self.grid.version, fire)
        if key != self._guide_key:
            ux, uy = self.shooter.direction()
            dots, end = trace(self.grid, SHOOTER_X, SHOOTER_Y, ux, uy, stop=not fire)
            self._guide, self._guide_key = (dots, end), key
        dots, end = self._guide
        for i, (x, y) in enumerate(dots[2:]):
            pygame.draw.circle(surf, (255, 255, 255), (int(x), int(y)), max(2, 5 - i // 12))
        if end is not None and not fire:
            cell = self.grid.nearest_empty(*end)
            if cell:
                x, y = self.grid.center(*cell)
                sprites.draw_ball(surf, self.current.key, x, y, alpha=90)

    def _draw_projectile(self, surf):
        p = self.proj
        for i, (x, y) in enumerate(p.trail):
            pygame.draw.circle(surf, (255, 255, 255) if p.kind != "fire" else (255, 160, 50),
                               (int(x), int(y)), max(1, int(2 + i * 0.6)))
        sprites.draw_ball(surf, p.key, p.x, p.y)

    def _draw_hud(self, surf):
        lv = self.level
        # left panels
        ui.panel(surf, (24, 24, 296, 176))
        ui.text(surf, "LEVEL %d" % self.n, 46, (255, 255, 255), (172, 62))
        ui.text(surf, lv.tier_name, 22, (255, 220, 120), (172, 106))
        ui.text(surf, lv.name, 20, (255, 120, 120) if lv.boss else (190, 205, 255), (172, 138))
        best = self.save.stars(self.n)
        for i in range(3):
            ui.draw_star(surf, (122 + i * 50, 172), 16, i < best)
        ui.panel(surf, (24, 216, 296, 240))
        ui.text(surf, "SCORE", 20, (170, 185, 230), (172, 246))
        ui.text(surf, str(self.score), 46, (255, 255, 255), (172, 284))
        ui.text(surf, "HIGH SCORE", 20, (170, 185, 230), (172, 330))
        ui.text(surf, str(max(self.save.data["high_score"], self.score)), 32, (255, 230, 140), (172, 362))
        ui.text(surf, "SHOTS LEFT", 20, (170, 185, 230), (172, 400))
        ui.text(surf, "Unlimited" if self.shots_left is None else str(self.shots_left), 36,
                (255, 255, 255) if self.shots_left is None or self.shots_left > 4 else (255, 110, 110), (172, 432))
        ui.panel(surf, (24, 472, 296, 150))
        ui.text(surf, "PROGRESS", 20, (170, 185, 230), (172, 500))
        frac = 1 - self.grid.count_colored() / self.initial
        bar = pygame.Rect(48, 520, 248, 20)
        pygame.draw.rect(surf, (40, 46, 82), bar, border_radius=10)
        if frac > 0:
            pygame.draw.rect(surf, (90, 210, 130), (bar.x, bar.y, max(12, int(bar.w * frac)), bar.h), border_radius=10)
        ui.text(surf, "%d%%" % int(frac * 100), 16, (255, 255, 255), bar.center, shadow=False)
        ui.draw_star(surf, (60, 576), 11)
        ui.draw_star(surf, (80, 576), 11)
        ui.draw_star(surf, (100, 576), 11)
        ui.text(surf, "in %d shots or less" % lv.t3, 18, (210, 220, 255), (120, 576), "midleft")
        ui.draw_star(surf, (60, 602), 11)
        ui.draw_star(surf, (80, 602), 11)
        ui.text(surf, "in %d shots or less" % lv.t2, 18, (210, 220, 255), (120, 602), "midleft")
        # right side
        for b in self.top_buttons:
            b.draw(surf)
        inv = self.player.inventory()
        for i, pid in enumerate(POWERUP_ORDER):
            rect = self.pb_rects[i]
            info = POWERUPS[pid]
            locked = self.n < info["unlock"]
            hover = rect.collidepoint(self.app.mouse) and not locked
            ui.panel(surf, rect, (40, 56, 120, 200) if hover else (10, 14, 36, 160), 14)
            sprites.draw_ball(surf, pid, rect.centerx, rect.y + 36, scale=1.15)
            ui.text(surf, info["name"], 17, (230, 235, 255), (rect.centerx, rect.y + 78))
            if not locked:
                cnt = inv.get(pid, 0)
                pygame.draw.circle(surf, (230, 70, 80) if cnt else (90, 95, 120), (rect.right - 16, rect.y + 16), 13)
                ui.text(surf, str(cnt), 17, (255, 255, 255), (rect.right - 16, rect.y + 16), shadow=False)
                ui.text(surf, str(i + 1), 14, (160, 175, 220), (rect.x + 12, rect.y + 12), shadow=False)
            else:
                ui.panel(surf, rect, (0, 0, 0, 140), 14, None)
                ui.draw_lock(surf, (rect.centerx, rect.y + 40), 26)
                ui.text(surf, "Level %d" % info["unlock"], 16, (255, 220, 120), (rect.centerx, rect.y + 78))
        if self.slow > 0:
            ui.text(surf, "SLOW-MO %.1fs" % self.slow, 24, (130, 190, 255), (1110, 520))
        ui.text(surf, "Click: shoot   Right-click / Space: swap", 17, (190, 200, 235), (1110, 600))
        ui.text(surf, "1-6: power-ups   P: pause   R: restart", 17, (190, 200, 235), (1110, 626))
        # next bubble label
        ui.text(surf, "NEXT", 18, (200, 215, 255), (SHOOTER_X - 125, SHOOTER_Y - 34))

    def _draw_toasts(self, surf):
        for i, (msg, t) in enumerate(self.toasts[-3:]):
            ui.panel(surf, (WIDTH // 2 - 230, 90 + i * 46, 460, 40), (10, 14, 40, 220), 14)
            ui.text(surf, msg, 20, (255, 235, 150), (WIDTH // 2, 110 + i * 46), alpha=int(255 * min(1, t * 2)))

    def _draw_end(self, surf):
        ui.dim(surf, 150)
        won = self.state == "won"
        t = self.overlay_t
        ui.panel(surf, (440, 100 if won else 160, 400, 520 if won else 400), (14, 18, 46, 240), 26)
        if won:
            s = 1 + 0.06 * math.sin(t * 4)
            ui.text(surf, "LEVEL COMPLETE!" if self.n < TOTAL_LEVELS else "YOU WON THE GAME!",
                    int(44 * s), (120, 255, 160), (WIDTH // 2, 150))
            ui.text(surf, "Congratulations!", 26, (255, 230, 140), (WIDTH // 2, 195))
            for i in range(3):
                k = max(0.0, min(1.0, (t - 0.3 - i * 0.4) / 0.35))
                size = 46 * (1 + 0.5 * math.sin(k * math.pi)) if k < 1 else 46
                if k > 0:
                    ui.draw_star(surf, (WIDTH // 2 - 90 + i * 90, 265), size * (0.4 + 0.6 * k), i < self.stars)
                else:
                    ui.draw_star(surf, (WIDTH // 2 - 90 + i * 90, 265), 30, False)
            ui.text(surf, "Score: %d" % self.score, 38, (255, 255, 255), (WIDTH // 2, 335))
            if self.new_best:
                ui.text(surf, "New best!", 24, (255, 210, 80), (WIDTH // 2, 372))
            elif self.reward:
                ui.text(surf, "Reward: +1 %s" % POWERUPS[self.reward[0]]["name"], 22, (170, 230, 255), (WIDTH // 2, 372))
        else:
            ui.text(surf, "GAME OVER", 58, (255, 100, 110), (WIDTH // 2, 215))
            ui.text(surf, self.reason, 24, (255, 225, 170), (WIDTH // 2, 275))
            ui.text(surf, "Final score: %d" % self.score, 36, (255, 255, 255), (WIDTH // 2, 335))
        for b in self.end_buttons:
            b.draw(surf)
