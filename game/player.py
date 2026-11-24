"""Player inventory / reward logic on top of the save file."""
import random

from .powerups import POWERUP_ORDER, POWERUPS


class Player:
    def __init__(self, save):
        self.save = save

    def inventory(self):
        return self.save.data["inventory"]

    def count(self, pid):
        return self.inventory().get(pid, 0)

    def use(self, pid):
        if self.count(pid) > 0:
            self.inventory()[pid] -= 1
            self.save.save()
            return True
        return False

    def grant_unlocks(self, level):
        """First time a power-up becomes available the player gets 2 of it."""
        granted = self.save.data["granted"]
        new = []
        for pid in POWERUP_ORDER:
            if level >= POWERUPS[pid]["unlock"] and pid not in granted:
                granted.append(pid)
                self.inventory()[pid] += 2
                new.append(pid)
        if new:
            self.save.save()
        return new

    def reward_random(self, level):
        """Winning a level gives one random unlocked power-up."""
        pool = [p for p in POWERUP_ORDER if level >= POWERUPS[p]["unlock"]]
        if not pool:
            return []
        pid = random.choice(pool)
        self.inventory()[pid] += 1
        self.save.save()
        return [pid]
