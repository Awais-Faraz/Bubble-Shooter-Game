"""Particles, falling bubbles, shock-wave rings, floating score text, confetti."""
import math
import random

import pygame

from .settings import WIDTH, HEIGHT, BOARD_LEFT, BOARD_RIGHT
from . import sprites, ui


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max", "color", "size", "g", "kind")

    def __init__(self, x, y, vx, vy, life, color, size, g=600.0, kind="circle"):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life = self.max = life
        self.color, self.size, self.g, self.kind = color, size, g, kind


class Effects:
    def __init__(self):
        self.parts = []
        self.falling = []     # [key, x, y, vx, vy]
        self.rings = []       # [x, y, r, max_r, t, max_t, color]
        self.texts = []       # [text, x, y, color, t, size]
        self.flashes = []     # [y, t, color]
        self.shake = 0.0

    # ---- spawners ----
    def burst(self, x, y, rgb, n=14, speed=280.0, size=6):
        for _ in range(n):
            a = random.uniform(0, 6.2832)
            s = random.uniform(0.3, 1.0) * speed
            self.parts.append(Particle(x, y, math.cos(a) * s, math.sin(a) * s - 60,
                                       random.uniform(0.35, 0.8), rgb, random.uniform(size * 0.5, size)))
        if len(self.parts) > 700:
            del self.parts[:250]

    def pop(self, x, y, rgb):
        self.burst(x, y, rgb, 12, 300, 6)
        self.burst(x, y, (255, 255, 255), 5, 220, 3)
        self.rings.append([x, y, 6, 34, 0.0, 0.3, rgb])

    def explosion(self, x, y, big=True):
        self.burst(x, y, (255, 170, 40), 40 if big else 20, 520, 9)
        self.burst(x, y, (255, 80, 30), 24, 380, 8)
        self.burst(x, y, (255, 240, 160), 14, 600, 4)
        self.rings.append([x, y, 10, 120 if big else 70, 0.0, 0.45, (255, 200, 90)])
        self.shake = max(self.shake, 9 if big else 4)

    def lightning_row(self, y):
        self.flashes.append([y, 0.0, (255, 245, 150)])
        for i in range(26):
            x = random.uniform(BOARD_LEFT, BOARD_RIGHT)
            self.parts.append(Particle(x, y + random.uniform(-10, 10), random.uniform(-80, 80),
                                       random.uniform(-160, 60), random.uniform(0.3, 0.6),
                                       (255, 245, 150), random.uniform(2, 5), 300))
        self.shake = max(self.shake, 6)

    def fall(self, key, x, y):
        self.falling.append([key, x, y, random.uniform(-90, 90), random.uniform(-260, -60)])

    def text(self, s, x, y, color=(255, 255, 255), size=26):
        self.texts.append([s, x, y, color, 0.0, size])

    def confetti(self, n=70):
        cols = [(255, 90, 110), (255, 200, 60), (90, 220, 120), (90, 170, 255), (200, 120, 255)]
        for _ in range(n):
            self.parts.append(Particle(random.uniform(0, WIDTH), random.uniform(-60, -5),
                                       random.uniform(-60, 60), random.uniform(60, 260),
                                       random.uniform(2.5, 4.0), random.choice(cols),
                                       random.uniform(5, 9), 120, "rect"))

    # ---- update / draw ----
    def update(self, dt):
        for p in self.parts:
            p.life -= dt
            p.vy += p.g * dt
            p.x += p.vx * dt
            p.y += p.vy * dt
        self.parts = [p for p in self.parts if p.life > 0 and p.y < HEIGHT + 40]
        for f in self.falling:
            f[4] += 1500 * dt
            f[1] += f[3] * dt
            f[2] += f[4] * dt
        self.falling = [f for f in self.falling if f[2] < HEIGHT + 60]
        for r in self.rings:
            r[4] += dt
            k = min(1.0, r[4] / r[5])
            r[2] = r[2] + (r[3] - r[2]) * min(1.0, dt * 10)
        self.rings = [r for r in self.rings if r[4] < r[5]]
        for t in self.texts:
            t[4] += dt
            t[2] -= 45 * dt
        self.texts = [t for t in self.texts if t[4] < 0.9]
        for f in self.flashes:
            f[1] += dt
        self.flashes = [f for f in self.flashes if f[1] < 0.35]
        self.shake = max(0.0, self.shake - 30 * dt)

    def draw(self, surf):
        for f in self.falling:
            sprites.draw_ball(surf, f[0], f[1], f[2])
        for fl in self.flashes:
            w = max(1, int(26 * (1 - fl[1] / 0.35)))
            pygame.draw.line(surf, fl[2], (BOARD_LEFT, fl[0]), (BOARD_RIGHT, fl[0]), w)
        for r in self.rings:
            k = r[4] / r[5]
            pygame.draw.circle(surf, r[6], (int(r[0]), int(r[1])), int(r[2]), max(1, int(4 * (1 - k))))
        for p in self.parts:
            k = max(0.0, p.life / p.max)
            sz = max(1, int(p.size * (0.4 + 0.6 * k)))
            if p.kind == "rect":
                pygame.draw.rect(surf, p.color, (int(p.x), int(p.y), sz, sz + 3))
            else:
                pygame.draw.circle(surf, p.color, (int(p.x), int(p.y)), sz)
        for t in self.texts:
            a = int(255 * (1 - t[4] / 0.9))
            ui.text(surf, t[0], t[5], t[3], (t[1], t[2]), alpha=a)
