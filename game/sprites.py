"""Procedurally drawn glossy bubble sprites (no image files needed)."""
import colorsys
import math

import pygame

from .settings import R, COLORS

_S = 2                 # supersampling factor for smooth edges
_cache = {}
_scaled = {}


def _shade(rgb, f):
    return tuple(max(0, min(255, int(v * f))) for v in rgb)


def _mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _canvas(rad):
    size = 2 * rad + 10
    return pygame.Surface((size * _S, size * _S), pygame.SRCALPHA), size


def _body(surf, size, rad, grad):
    """Draw shadow + radial-gradient body. grad(t) -> rgb, t: 0 at rim .. 1 at centre."""
    cx = cy = (size // 2 - 1) * _S
    r = rad * _S
    pygame.draw.circle(surf, (0, 0, 0, 70), (cx + 3 * _S, cy + 4 * _S), r)
    for i in range(r, 0, -1):
        t = 1 - i / r
        off = int(r * 0.30 * t)
        pygame.draw.circle(surf, grad(t) + (255,), (cx - off, cy - off), i)
    return cx, cy, r


def _finish(surf, size, cx, cy, r, rim):
    pygame.draw.circle(surf, rim + (255,), (cx, cy), r, max(2, _S))
    hl = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    pygame.draw.ellipse(hl, (255, 255, 255, 170),
                        (int(cx - r * 0.62), int(cy - r * 0.74), int(r * 0.80), int(r * 0.46)))
    pygame.draw.circle(hl, (255, 255, 255, 60), (int(cx + r * 0.34), int(cy + r * 0.46)), int(r * 0.2))
    surf.blit(hl, (0, 0))
    return pygame.transform.smoothscale(surf, (size, size))


def _ball_color(rgb, rad):
    surf, size = _canvas(rad)

    def grad(t):
        return _mix(_shade(rgb, 0.50 + 0.65 * t), (255, 255, 255), max(0.0, t - 0.55) * 0.7)

    cx, cy, r = _body(surf, size, rad, grad)
    return _finish(surf, size, cx, cy, r, _shade(rgb, 0.45))


def _poly(surf, cx, cy, r, pts, color, width=0):
    pygame.draw.polygon(surf, color, [(cx + x * r, cy + y * r) for x, y in pts], width)


def _ball_special(kind, rad):
    surf, size = _canvas(rad)
    bases = {"stone": (125, 130, 145), "bomb": (40, 42, 66), "fire": (240, 80, 30),
             "lightning": (250, 205, 60), "extra": (60, 190, 100), "slow": (70, 130, 240)}
    if kind == "rainbow":
        def grad(t):
            h = (1 - t) * 0.8
            return tuple(int(v * 255) for v in colorsys.hsv_to_rgb(h, 0.65, 1.0))
        rim = (90, 90, 120)
    else:
        base = bases[kind]

        def grad(t, base=base):
            return _mix(_shade(base, 0.50 + 0.65 * t), (255, 255, 255), max(0.0, t - 0.55) * 0.6)
        rim = _shade(base, 0.45)
    cx, cy, r = _body(surf, size, rad, grad)

    if kind == "stone":
        w = max(2, _S * 2)
        for line in ([(-.5, -.6), (-.1, -.15), (-.35, .2), (.05, .55)], [(.55, -.3), (.2, .05), (.4, .5)]):
            pygame.draw.lines(surf, (70, 72, 84), False,
                              [(cx + x * r, cy + y * r) for x, y in line], w)
    elif kind == "bomb":
        pts = []
        for i in range(16):
            a = i * math.pi / 8
            rr = 0.62 if i % 2 == 0 else 0.30
            pts.append((math.cos(a) * rr, math.sin(a) * rr))
        _poly(surf, cx, cy, r, pts, (255, 150, 30))
        pygame.draw.circle(surf, (255, 235, 100), (cx, cy), int(r * 0.2))
    elif kind == "fire":
        flame = [(0, -.75), (.4, -.2), (.5, .3), (.25, .65), (-.25, .65), (-.5, .3), (-.35, -.1), (-.1, -.3)]
        _poly(surf, cx, cy, r, flame, (255, 205, 60))
        _poly(surf, cx, cy, r, [(x * .55, y * .55 + .15) for x, y in flame], (255, 250, 210))
    elif kind == "lightning":
        bolt = [(.18, -.8), (-.45, .1), (-.05, .1), (-.2, .8), (.45, -.15), (.05, -.15)]
        _poly(surf, cx, cy, r, bolt, (255, 255, 255))
        _poly(surf, cx, cy, r, bolt, (110, 80, 0), _S)
    elif kind == "extra":
        f = pygame.font.SysFont("arial,segoeui,dejavusans", int(r * 1.0), bold=True)
        img = f.render("+5", True, (255, 255, 255))
        surf.blit(img, img.get_rect(center=(cx, cy)))
    elif kind == "slow":
        pygame.draw.circle(surf, (255, 255, 255), (cx, cy), int(r * .6), max(2, _S * 2))
        pygame.draw.line(surf, (255, 255, 255), (cx, cy), (cx, cy - int(r * .4)), max(2, _S * 2))
        pygame.draw.line(surf, (255, 255, 255), (cx, cy), (cx + int(r * .3), cy + int(r * .1)), max(2, _S * 2))
    return _finish(surf, size, cx, cy, r, rim)


def get_ball(key, rad=R):
    k = (key, rad)
    s = _cache.get(k)
    if s is None:
        s = _ball_color(COLORS[key], rad) if isinstance(key, int) else _ball_special(key, rad)
        _cache[k] = s
    return s


def draw_ball(surf, key, x, y, scale=1.0, alpha=255, rad=R):
    """Blit a bubble sprite centred at (x, y)."""
    s = get_ball(key, rad)
    size = s.get_width()
    c = size // 2 - 1
    if abs(scale - 1.0) > 0.01:
        sk = (key, rad, round(scale, 2))
        sc = _scaled.get(sk)
        if sc is None:
            if len(_scaled) > 300:
                _scaled.clear()
            ns = max(2, int(size * scale))
            sc = pygame.transform.smoothscale(s, (ns, ns))
            _scaled[sk] = sc
        s = sc
        c = int(c * scale)
    if alpha < 255:
        s = s.copy()
        s.set_alpha(alpha)
    surf.blit(s, (int(x) - c, int(y) - c))
