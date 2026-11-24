"""Procedurally synthesised sound effects + background music (no asset files)."""
import array
import math
import random

import pygame


class Audio:
    @staticmethod
    def pre_init():
        try:
            pygame.mixer.pre_init(22050, -16, 1, 512)
        except Exception:
            pass

    def __init__(self, settings):
        self.settings = settings
        self.ok = False
        self.sounds = {}
        self.music = None
        self.channel = None
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            self.rate, fmt, self.channels = pygame.mixer.get_init()
            if abs(fmt) != 16:
                raise RuntimeError("unsupported mixer format")
            pygame.mixer.set_num_channels(16)
            pygame.mixer.set_reserved(1)
            self.channel = pygame.mixer.Channel(0)
            self._build()
            self.ok = True
        except Exception as ex:
            print("Audio disabled:", ex)
        self.apply()

    # ---- synthesis ----
    def _tone(self, f0, f1, dur, vol=0.5, kind="sine", decay=4.0):
        n = int(self.rate * dur)
        out, ph = [], 0.0
        attack = max(1, int(0.004 * self.rate))
        for i in range(n):
            t = i / n
            ph += 2 * math.pi * (f0 + (f1 - f0) * t) / self.rate
            if kind == "sine":
                s = math.sin(ph)
            elif kind == "square":
                s = 0.5 if math.sin(ph) > 0 else -0.5
            elif kind == "saw":
                s = ((ph / (2 * math.pi)) % 1.0) * 2 - 1
            else:
                s = random.uniform(-1, 1)
            out.append(s * math.exp(-decay * t) * min(1.0, i / attack) * vol)
        return out

    @staticmethod
    def _mix(a, b, offset=0):
        if len(a) < offset + len(b):
            a.extend([0.0] * (offset + len(b) - len(a)))
        for i, v in enumerate(b):
            a[offset + i] += v
        return a

    def _sound(self, samples, vol=1.0):
        arr = array.array("h")
        for s in samples:
            v = int(max(-1.0, min(1.0, s)) * 30000)
            for _ in range(self.channels):
                arr.append(v)
        snd = pygame.mixer.Sound(buffer=arr.tobytes())
        snd.set_volume(vol)
        return snd

    def _build(self):
        t = self._tone
        self.sounds["shoot"] = self._sound(t(500, 1000, 0.12, 0.5, "sine", 5))
        self.sounds["pop"] = self._sound(self._mix(t(0, 0, 0.08, 0.35, "noise", 18), t(700, 250, 0.14, 0.5, "sine", 9)))
        self.sounds["click"] = self._sound(t(1000, 1300, 0.05, 0.4, "sine", 8))
        self.sounds["bounce"] = self._sound(t(420, 300, 0.05, 0.3, "sine", 6))
        self.sounds["thud"] = self._sound(t(220, 90, 0.1, 0.6, "sine", 8))
        self.sounds["fall"] = self._sound(t(900, 200, 0.25, 0.3, "sine", 4))
        self.sounds["power"] = self._sound(t(300, 1200, 0.3, 0.4, "sine", 2))
        self.sounds["bomb"] = self._sound(self._mix(t(0, 0, 0.5, 0.6, "noise", 6), t(120, 40, 0.5, 0.8, "sine", 5)))
        win = []
        for i, f in enumerate((523, 659, 784, 1047, 1318)):
            self._mix(win, t(f, f, 0.2, 0.45, "sine", 3), int(i * 0.13 * self.rate))
        self.sounds["win"] = self._sound(win)
        lose = []
        for i, f in enumerate((392, 349, 311, 262)):
            self._mix(lose, t(f, f * 0.97, 0.26, 0.3, "saw", 3), int(i * 0.24 * self.rate))
        self.sounds["lose"] = self._sound(lose)
        self.music = self._sound(self._music(), 1.0)

    def _music(self):
        """8-second looping arpeggio (C - Am - F - G) with bass and a simple melody."""
        chords = [(261.6, 329.6, 392.0), (220.0, 261.6, 329.6), (174.6, 220.0, 261.6), (196.0, 246.9, 293.7)]
        pattern = [0, 1, 2, 1, 0, 1, 2, 1]
        buf = [0.0] * int(8.0 * self.rate)
        for bar, ch in enumerate(chords):
            start = int(bar * 2.0 * self.rate)
            self._mix(buf, self._tone(ch[0] / 2, ch[0] / 2, 1.9, 0.22, "sine", 1.2), start)
            for i, idx in enumerate(pattern):
                self._mix(buf, self._tone(ch[idx] * 2, ch[idx] * 2, 0.24, 0.10, "sine", 5),
                          start + int(i * 0.25 * self.rate))
            for j, idx in enumerate((2, 1, 0, 2)):
                self._mix(buf, self._tone(ch[idx] * 4, ch[idx] * 4, 0.45, 0.05, "sine", 4),
                          start + int(j * 0.5 * self.rate))
        return buf[:int(8.0 * self.rate)]

    # ---- control ----
    def play(self, name):
        if self.ok and self.settings.get("sfx", True):
            snd = self.sounds.get(name)
            if snd:
                snd.set_volume(self.settings.get("sfx_volume", 0.8))
                snd.play()

    def apply(self):
        """Re-apply music/sfx settings (call after the player changes them)."""
        if not self.ok:
            return
        try:
            self.channel.set_volume(self.settings.get("music_volume", 0.5) * 0.6)
            if self.settings.get("music", True):
                if not self.channel.get_busy():
                    self.channel.play(self.music, loops=-1)
            else:
                self.channel.stop()
        except Exception:
            pass
