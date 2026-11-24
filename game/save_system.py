"""Persistent JSON progress saving."""
import copy
import json
import os
import shutil

from .settings import data_path, TOTAL_LEVELS

DEFAULTS = {
    "version": 1,
    "unlocked": 1,
    "completed": [],
    "stars": {},
    "best_scores": {},
    "total_score": 0,
    "high_score": 0,
    "settings": {"music": True, "sfx": True, "music_volume": 0.5,
                 "sfx_volume": 0.8, "fullscreen": False},
    "inventory": {"bomb": 0, "rainbow": 0, "lightning": 0, "extra": 0, "fire": 0, "slow": 0},
    "granted": [],
}


class SaveSystem:
    def __init__(self, path=None):
        self.path = path or data_path("progress.json")
        self.data = copy.deepcopy(DEFAULTS)
        self.error = None
        self.load()

    # ---- file io ----
    def load(self):
        if not os.path.exists(self.path):
            self.save()
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if not isinstance(raw, dict):
                raise ValueError("bad save format")
            for k, default in DEFAULTS.items():
                if k not in raw:
                    continue
                if k in ("settings", "inventory"):
                    if isinstance(raw[k], dict):
                        for kk in default:
                            if kk in raw[k]:
                                self.data[k][kk] = raw[k][kk]
                elif type(raw[k]) == type(default):
                    self.data[k] = raw[k]
            self._sanitize()
        except Exception as ex:          # corrupted file -> keep a backup, start fresh
            self.error = "Save file was unreadable: %s" % ex
            try:
                shutil.copyfile(self.path, self.path + ".bak")
            except OSError:
                pass
            self.data = copy.deepcopy(DEFAULTS)
            self.save()

    def _sanitize(self):
        d = self.data
        d["unlocked"] = max(1, min(TOTAL_LEVELS, int(d["unlocked"])))
        d["completed"] = sorted({int(x) for x in d["completed"] if 1 <= int(x) <= TOTAL_LEVELS})
        s = d["settings"]
        s["music_volume"] = max(0.0, min(1.0, float(s["music_volume"])))
        s["sfx_volume"] = max(0.0, min(1.0, float(s["sfx_volume"])))

    def save(self):
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
            os.replace(tmp, self.path)
            return True
        except OSError as ex:
            self.error = "Could not save progress: %s" % ex
            return False

    # ---- helpers ----
    @property
    def settings(self):
        return self.data["settings"]

    @property
    def unlocked(self):
        return self.data["unlocked"]

    def is_unlocked(self, n):
        return n <= self.data["unlocked"]

    def is_completed(self, n):
        return n in self.data["completed"]

    def stars(self, n):
        return int(self.data["stars"].get(str(n), 0))

    def complete_level(self, n, score, stars):
        """Record a win. Returns True if the score is a new best for this level."""
        d = self.data
        new_best = score > d["best_scores"].get(str(n), 0)
        if n not in d["completed"]:
            d["completed"].append(n)
            d["completed"].sort()
        d["stars"][str(n)] = max(self.stars(n), stars)
        if new_best:
            d["best_scores"][str(n)] = score
        d["total_score"] += score
        d["high_score"] = max(d["high_score"], score)
        d["unlocked"] = max(d["unlocked"], min(TOTAL_LEVELS, n + 1))
        self.save()
        return new_best

    def reset(self):
        keep = copy.deepcopy(self.data["settings"])
        self.data = copy.deepcopy(DEFAULTS)
        self.data["settings"] = keep
        self.save()
