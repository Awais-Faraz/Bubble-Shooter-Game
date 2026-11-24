"""UI toolkit: fonts, text, buttons, toggles, sliders, stars, panels."""
import math

import pygame

FONT_NAMES = "segoeui,arial,helvetica,verdana,dejavusans"
on_click = None                     # set by the app: plays the click sound

_fonts = {}
_text_cache = {}
_grad_cache = {}
_panel_cache = {}


def font(size, bold=True):
    k = (size, bold)
    f = _fonts.get(k)
    if f is None:
        f = pygame.font.SysFont(FONT_NAMES, size, bold=bold)
        _fonts[k] = f
    return f


def render(s, size, color, bold=True):
    k = (s, size, color, bold)
    img = _text_cache.get(k)
    if img is None:
        if len(_text_cache) > 700:
            _text_cache.clear()
        img = font(size, bold).render(s, True, color)
        _text_cache[k] = img
    return img


def text(surf, s, size, color, pos, anchor="center", bold=True, shadow=True, alpha=255):
    """Draw text. anchor is any pygame Rect attribute (center, midleft, topright...)."""
    img = render(s, size, tuple(color)[:3], bold)
    rect = img.get_rect()
    setattr(rect, anchor, (int(pos[0]), int(pos[1])))
    if shadow:
        sh = render(s, size, (0, 0, 0), bold)
        sh.set_alpha(min(120, alpha))
        surf.blit(sh, rect.move(2, 2))
    if alpha < 255:
        img = img.copy()
        img.set_alpha(alpha)
    surf.blit(img, rect)
    return rect


def gradient_round(w, h, c1, c2, radius):
    k = (w, h, c1, c2, radius)
    s = _grad_cache.get(k)
    if s is None:
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(h):
            t = y / max(1, h - 1)
            pygame.draw.line(s, tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3)), (0, y), (w, y))
        mask = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, w, h), border_radius=radius)
        s.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        _grad_cache[k] = s
    return s


def panel(surf, rect, color=(10, 14, 36, 150), radius=18, border=(255, 255, 255, 40)):
    """Translucent rounded panel."""
    rect = pygame.Rect(rect)
    k = (rect.w, rect.h, color, radius, border)
    s = _panel_cache.get(k)
    if s is None:
        s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        pygame.draw.rect(s, color, (0, 0, rect.w, rect.h), border_radius=radius)
        if border:
            pygame.draw.rect(s, border, (0, 0, rect.w, rect.h), 2, border_radius=radius)
        _panel_cache[k] = s
    surf.blit(s, rect.topleft)


_dim_cache = {}


def dim(surf, alpha=150):
    s = _dim_cache.get((surf.get_size(), alpha))
    if s is None:
        s = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        s.fill((0, 0, 0, alpha))
        _dim_cache[(surf.get_size(), alpha)] = s
    surf.blit(s, (0, 0))


def _lighten(c, f):
    return tuple(min(255, int(v * f)) for v in c)


class Button:
    """Animated button: hover grows, press shrinks, callback fires on release."""

    def __init__(self, rect, label, callback, color=(70, 140, 255), size=30, enabled=True):
        self.rect = pygame.Rect(rect)
        self.label, self.callback, self.color, self.size = label, callback, color, size
        self.enabled = enabled
        self.scale = 1.0
        self.pressed = False
        self.hover = False

    def handle_event(self, e):
        if not self.enabled:
            return False
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.rect.collidepoint(e.pos):
            self.pressed = True
            return True
        if e.type == pygame.MOUSEBUTTONUP and e.button == 1 and self.pressed:
            self.pressed = False
            if self.rect.collidepoint(e.pos):
                if on_click:
                    on_click()
                self.callback()
            return True
        return False

    def update(self, dt, mouse):
        self.hover = self.enabled and self.rect.collidepoint(mouse)
        target = 0.94 if self.pressed else (1.06 if self.hover else 1.0)
        self.scale += (target - self.scale) * min(1.0, dt * 18)

    def draw(self, surf):
        w, h = int(self.rect.w * self.scale), int(self.rect.h * self.scale)
        r = pygame.Rect(0, 0, w, h)
        r.center = self.rect.center
        base = self.color if self.enabled else (95, 100, 115)
        if self.hover:
            base = _lighten(base, 1.15)
        radius = h // 3
        panel(surf, (r.x, r.y + 5, w, h), (0, 0, 0, 90), radius, None)
        surf.blit(gradient_round(w, h, _lighten(base, 1.25), _lighten(base, 0.72), radius), r.topleft)
        panel(surf, (r.x + 6, r.y + 4, w - 12, h // 2 - 4), (255, 255, 255, 38), radius // 2, None)
        pygame.draw.rect(surf, (255, 255, 255), r, 2, border_radius=radius)
        text(surf, self.label, self.size, (255, 255, 255), r.center)


class Toggle:
    def __init__(self, center, value, callback):
        self.rect = pygame.Rect(0, 0, 74, 36)
        self.rect.center = center
        self.value, self.callback = value, callback
        self.anim = 1.0 if value else 0.0

    def handle_event(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.rect.collidepoint(e.pos):
            self.value = not self.value
            if on_click:
                on_click()
            self.callback(self.value)
            return True
        return False

    def update(self, dt, mouse=None):
        self.anim += ((1.0 if self.value else 0.0) - self.anim) * min(1.0, dt * 14)

    def draw(self, surf):
        col = tuple(int(a + (b - a) * self.anim) for a, b in zip((90, 95, 120), (60, 200, 110)))
        pygame.draw.rect(surf, col, self.rect, border_radius=18)
        pygame.draw.rect(surf, (255, 255, 255), self.rect, 2, border_radius=18)
        x = self.rect.x + 18 + int(38 * self.anim)
        pygame.draw.circle(surf, (255, 255, 255), (x, self.rect.centery), 13)
        text(surf, "ON" if self.value else "OFF", 14, (255, 255, 255),
             (self.rect.x + (20 if self.value else 54), self.rect.centery), shadow=False)


class Slider:
    def __init__(self, rect, value, callback):
        self.rect = pygame.Rect(rect)
        self.value, self.callback = value, callback
        self.drag = False

    def _set(self, x):
        self.value = max(0.0, min(1.0, (x - self.rect.x) / self.rect.w))
        self.callback(self.value)

    def handle_event(self, e):
        grab = self.rect.inflate(20, 30)
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and grab.collidepoint(e.pos):
            self.drag = True
            self._set(e.pos[0])
            return True
        if e.type == pygame.MOUSEMOTION and self.drag:
            self._set(e.pos[0])
            return True
        if e.type == pygame.MOUSEBUTTONUP and e.button == 1 and self.drag:
            self.drag = False
            if on_click:
                on_click()
            return True
        return False

    def update(self, dt, mouse=None):
        pass

    def draw(self, surf):
        r = pygame.Rect(self.rect.x, self.rect.centery - 5, self.rect.w, 10)
        pygame.draw.rect(surf, (50, 56, 90), r, border_radius=5)
        f = pygame.Rect(r.x, r.y, int(r.w * self.value), r.h)
        pygame.draw.rect(surf, (90, 170, 255), f, border_radius=5)
        pygame.draw.circle(surf, (255, 255, 255), (r.x + int(r.w * self.value), r.centery), 14)
        pygame.draw.circle(surf, (90, 170, 255), (r.x + int(r.w * self.value), r.centery), 14, 3)


def draw_star(surf, center, size, filled=True, color=(255, 205, 40)):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = size if i % 2 == 0 else size * 0.45
        pts.append((center[0] + math.cos(a) * rr, center[1] + math.sin(a) * rr))
    pygame.draw.polygon(surf, color if filled else (70, 76, 105), pts)
    pygame.draw.polygon(surf, (255, 245, 190) if filled else (110, 118, 150), pts, max(1, int(size / 9)))


def draw_lock(surf, center, size, color=(190, 195, 215)):
    x, y = center
    w, h = size, int(size * 0.75)
    pygame.draw.arc(surf, color, (x - w * 0.32, y - h * 0.95, w * 0.64, h * 0.9), 0, math.pi, max(2, size // 7))
    pygame.draw.rect(surf, color, (x - w // 2, y - h // 5, w, h), border_radius=4)
    pygame.draw.circle(surf, (70, 75, 100), (x, y + h // 5), max(2, size // 8))
