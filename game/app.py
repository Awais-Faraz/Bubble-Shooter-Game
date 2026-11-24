"""Application shell: window, scaling, scene switching with fade transitions."""
import sys

import pygame

from .settings import WIDTH, HEIGHT, FPS
from .audio import Audio
from .save_system import SaveSystem
from . import ui, sprites


class App:
    def __init__(self):
        Audio.pre_init()
        pygame.init()
        pygame.display.set_caption("Bubble Shooter")
        self.save = SaveSystem()
        self.window = None
        self._make_window(self.save.settings.get("fullscreen", False))
        self.screen = pygame.Surface((WIDTH, HEIGHT)).convert()
        try:
            pygame.display.set_icon(sprites.get_ball(0))
        except Exception:
            pass
        self.audio = Audio(self.save.settings)
        ui.on_click = lambda: self.audio.play("click")
        self.clock = pygame.time.Clock()
        self.mouse = (0, 0)
        self.running = True
        self.scene = None
        self.pending = None
        self.fade = 0.0
        self.fade_state = None
        self.fade_img = pygame.Surface((WIDTH, HEIGHT))
        self.fade_img.fill((0, 0, 0))

    # ---- window ----
    def _make_window(self, full):
        if full:
            self.window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.window = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)

    def set_fullscreen(self, flag):
        self.save.settings["fullscreen"] = bool(flag)
        self.save.save()
        self._make_window(flag)

    def _layout(self):
        ww, wh = self.window.get_size()
        s = min(ww / WIDTH, wh / HEIGHT)
        sw, sh = max(1, int(WIDTH * s)), max(1, int(HEIGHT * s))
        return s, sw, sh, (ww - sw) // 2, (wh - sh) // 2

    def to_logical(self, pos):
        s, _, _, ox, oy = self._layout()
        return ((pos[0] - ox) / s, (pos[1] - oy) / s)

    def quit(self):
        self.running = False

    # ---- scenes ----
    def goto(self, factory):
        if self.scene is None:
            self.scene = factory()
        else:
            self.pending = factory
            if self.fade_state != "out":
                self.fade_state = "out"

    def _fade_update(self, dt):
        if self.fade_state == "out":
            self.fade += dt / 0.18 * 255
            if self.fade >= 255:
                self.fade = 255
                if self.pending:
                    factory, self.pending = self.pending, None
                    self.scene = factory()
                self.fade_state = "in"
        elif self.fade_state == "in":
            self.fade -= dt / 0.18 * 255
            if self.fade <= 0:
                self.fade, self.fade_state = 0, None

    def _translate(self, e):
        if e.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            d = dict(e.dict)
            d["pos"] = self.to_logical(e.pos)
            return pygame.event.Event(e.type, d)
        return e

    # ---- main loop ----
    def run(self):
        from .scenes import MainMenu
        self.goto(lambda: MainMenu(self))
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.running = False
                elif e.type == pygame.KEYDOWN and e.key == pygame.K_F11:
                    self.set_fullscreen(not self.save.settings.get("fullscreen", False))
                elif self.fade_state is None and self.scene is not None:
                    self.scene.handle_event(self._translate(e))
            self.mouse = self.to_logical(pygame.mouse.get_pos())
            self._fade_update(dt)
            if self.scene is not None:
                self.scene.update(dt)
                self.scene.draw(self.screen)
            if self.fade > 0:
                self.fade_img.set_alpha(int(self.fade))
                self.screen.blit(self.fade_img, (0, 0))
            self._present()
        self.save.save()
        pygame.quit()

    def _present(self):
        s, sw, sh, ox, oy = self._layout()
        self.window.fill((0, 0, 0))
        if (sw, sh) == (WIDTH, HEIGHT):
            self.window.blit(self.screen, (ox, oy))
        else:
            self.window.blit(pygame.transform.smoothscale(self.screen, (sw, sh)), (ox, oy))
        pygame.display.flip()
