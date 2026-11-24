"""Animated gradient background with floating bubbles and twinkling stars."""
import colorsys
import math
import random

import pygame

from .settings import WIDTH, HEIGHT

HUES = [0.60, 0.52, 0.45, 0.35, 0.12, 0.02, 0.92, 0.80, 0.72, 0.66]
_grad_cache = {}
_bub_cache = {}


def _rgb(h, s, v):
    return tuple(int(c * 255) for c in colorsys.hsv_to_rgb(h % 1.0, s, v))


def _gradient(hue):
    surf = _grad_cache.get(hue)
    if surf is None:
        surf = pygame.Surface((WIDTH, HEIGHT)).convert()
        top, bot = _rgb(hue, 0.65, 0.34), _rgb(hue + 0.07, 0.80, 0.10)
        for y in range(HEIGHT):
            t = y / (HEIGHT - 1)
            col = tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3))
            pygame.draw.line(surf, col, (0, y), (WIDTH, y))
        _grad_cache[hue] = surf
    return surf


def _bubble(r):
    s = _bub_cache.get(r)
    if s is None:
        s = pygame.Surface((2 * r + 4, 2 * r + 4), pygame.SRCALPHA)
        pygame.draw.circle(s, (255, 255, 255, 20), (r + 2, r + 2), r)
        pygame.draw.circle(s, (255, 255, 255, 70), (r + 2, r + 2), r, 2)
        pygame.draw.ellipse(s, (255, 255, 255, 80), (int(r * 0.45), int(r * 0.35), int(r * 0.55), int(r * 0.3)))
        _bub_cache[r] = s
    return s


class Background:
    def __init__(self, tier=0):
        self.t = 0.0
        self.surface = _gradient(HUES[tier % len(HUES)])
        rnd = random.Random(tier + 5)
        self.bubbles = [[rnd.uniform(0, WIDTH), rnd.uniform(0, HEIGHT), rnd.choice((10, 14, 20, 28, 38, 50)),
                         rnd.uniform(12, 42), rnd.uniform(0, 6.28)] for _ in range(26)]
        self.stars = [(rnd.randint(0, WIDTH), rnd.randint(0, HEIGHT), rnd.uniform(0, 6.28), rnd.choice((1, 1, 2)))
                      for _ in range(55)]

    def update(self, dt):
        self.t += dt
        for b in self.bubbles:
            b[1] -= b[3] * dt
            if b[1] < -60:
                b[1] = HEIGHT + 60
                b[0] = random.uniform(0, WIDTH)

    def draw(self, surf):
        surf.blit(self.surface, (0, 0))
        for x, y, ph, sz in self.stars:
            v = int(90 + 120 * (0.5 + 0.5 * math.sin(self.t * 2 + ph)))
            pygame.draw.circle(surf, (v, v, min(255, v + 20)), (x, y), sz)
        for b in self.bubbles:
            surf.blit(_bubble(b[2]), (int(b[0] + math.sin(self.t + b[4]) * 18) - b[2], int(b[1]) - b[2]))
