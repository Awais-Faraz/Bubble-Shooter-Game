"""Shooter (cannon), loaded shots and projectiles."""
import math

import pygame

from .settings import SHOOTER_X, SHOOTER_Y
from . import sprites


class Shot:
    """A bubble waiting to be fired. kind: normal / bomb / rainbow / fire / lightning."""

    def __init__(self, kind="normal", color=0):
        self.kind, self.color = kind, color

    @property
    def key(self):
        return self.color if self.kind == "normal" else self.kind


class Projectile:
    def __init__(self, shot, ux, uy):
        self.kind, self.color = shot.kind, shot.color
        self.x, self.y = float(SHOOTER_X), float(SHOOTER_Y)
        self.ux, self.uy = ux, uy
        self.travel = 0.0
        self.trail = []

    @property
    def key(self):
        return self.color if self.kind == "normal" else self.kind


class Shooter:
    MIN_ANGLE = 0.17          # radians above horizontal

    def __init__(self):
        self.angle = -math.pi / 2
        self.recoil = 0.0

    def aim(self, mx, my):
        dx, dy = mx - SHOOTER_X, my - SHOOTER_Y
        if dy >= -2:
            a = -self.MIN_ANGLE if dx >= 0 else -math.pi + self.MIN_ANGLE
        else:
            a = math.atan2(dy, dx)
            a = max(-math.pi + self.MIN_ANGLE, min(-self.MIN_ANGLE, a))
        self.angle = a

    def direction(self):
        return math.cos(self.angle), math.sin(self.angle)

    def update(self, dt):
        self.recoil = max(0.0, self.recoil - dt * 6)

    def draw(self, surf, current, nxt):
        dx, dy = self.direction()
        px, py = -dy, dx
        c = (SHOOTER_X, SHOOTER_Y)
        pygame.draw.circle(surf, (20, 24, 48), (c[0], c[1] + 12), 46)
        pygame.draw.circle(surf, (95, 115, 180), (c[0], c[1] + 12), 46, 4)
        pygame.draw.circle(surf, (48, 56, 100), (c[0], c[1] + 12), 38)
        length = 58 - self.recoil * 10
        for w, col in ((17, (40, 50, 100)), (13, (80, 100, 175)), (6, (130, 155, 230))):
            pts = [(c[0] + px * w, c[1] + py * w), (c[0] - px * w, c[1] - py * w),
                   (c[0] - px * w + dx * length, c[1] - py * w + dy * length),
                   (c[0] + px * w + dx * length, c[1] + py * w + dy * length)]
            pygame.draw.polygon(surf, col, pts)
        pygame.draw.circle(surf, (110, 135, 215), (int(c[0] + dx * length), int(c[1] + dy * length)), 15)
        if current is not None:
            sprites.draw_ball(surf, current.key, c[0] - dx * self.recoil * 6, c[1] - dy * self.recoil * 6)
        if nxt is not None:
            sprites.draw_ball(surf, nxt.key, SHOOTER_X - 125, SHOOTER_Y + 6, scale=0.85)
