"""Pure Python session state, playback schedules, recall rules and scoring."""
from dataclasses import dataclass, asdict
from datetime import date
import hashlib
import math
import random

MODES = {
    "classic": ("Classic Sequence", "Watch the tiles. Repeat their order.", "Remember the sequence"),
    "pattern": ("Pattern Recall", "Remember locations, in any order.", "See the whole pattern"),
    "reverse": ("Reverse Sequence", "Watch forward. Recall backward.", "Give your focus a twist"),
    "time_attack": ("Time Attack", "Complete rounds before time runs out.", "Make every second count"),
    "practice": ("Practice Studio", "Your grid, your speed, your rules.", "Learn without pressure"),
}
RULES = {
    "Easy": {"grid": 3, "length": 3, "lives": 3, "flash": .8, "gap": .24, "recall": 18},
    "Medium": {"grid": 4, "length": 4, "lives": 2, "flash": .6, "gap": .2, "recall": 14},
    "Hard": {"grid": 5, "length": 5, "lives": 1, "flash": .42, "gap": .16, "recall": 10},
}


@dataclass
class Settings:
    difficulty: str = "Medium"
    duration: int = 60
    grid: int = 4
    length: int = 4
    playback: str = "Normal"
    practice_style: str = "Sequence"
    volume: int = 50
    theme: str = "Iris"
    reduced_motion: bool = False
    fps: int = 120

    @classmethod
    def from_dict(cls, data):
        result = cls()
        if not isinstance(data, dict):
            return result
        choices = {"difficulty": tuple(RULES), "duration": (60, 90, 120), "grid": (3, 4, 5, 6, 8),
                   "length": (3, 4, 6, 8, 12), "playback": ("Slow", "Normal", "Fast"),
                   "practice_style": ("Sequence", "Pattern", "Reverse"), "volume": (0, 25, 50, 75, 100),
                   "theme": ("Iris", "Ocean", "Amber", "High contrast"), "fps": (60, 120, 144)}
        for key, options in choices.items():
            value = data.get(key)
            if type(value) is type(options[0]) and value in options:
                setattr(result, key, value)
        if type(data.get("reduced_motion")) is bool:
            result.reduced_motion = data["reduced_motion"]
        return result


def daily_seed(day=None):
    return int.from_bytes(hashlib.sha256(("memtrix-2:" + (day or date.today()).isoformat()).encode()).digest()[:8], "big")


class Session:
    """Only active updates consume time. Drawing never changes the game rules."""
    def __init__(self, mode="classic", settings=None, seed=None, daily=False):
        if mode not in MODES:
            raise ValueError("Unknown game mode")
        self.settings = Settings.from_dict(asdict(settings or Settings()))
        self.daily = bool(daily)
        self.challenge_date = date.today().isoformat() if daily else None
        if daily:
            mode = "time_attack"
            self.settings = Settings(difficulty="Medium", duration=60)
            seed = daily_seed() if seed is None else seed
        self.mode = mode
        self.seed = seed if seed is not None else random.SystemRandom().randrange(2**63)
        self.rng = random.Random(self.seed)
        self.rule = RULES[self.settings.difficulty]
        self.lives = None if mode in ("practice", "time_attack") else self.rule["lives"]
        self.elapsed = 0.0
        self.duration = self.settings.duration if mode == "time_attack" else None
        self.score = self.rounds_correct = self.rounds_failed = self.selections = self.correct_selections = 0
        self.mistakes = self.timeouts = self.longest = self.streak = self.best_streak = 0
        self.recall_sum = 0.0
        self.hints = 0
        self.assisted = mode == "practice"
        self.finished = False
        self.pending_finish = False
        self.reason = ""
        self.events = []
        self._begin_round()

    @property
    def style(self):
        if self.mode == "practice":
            return {"Sequence": "classic", "Pattern": "pattern", "Reverse": "reverse"}[self.settings.practice_style]
        return "classic" if self.mode == "time_attack" else self.mode

    @property
    def accuracy(self):
        return 100 * self.correct_selections / self.selections if self.selections else 0.0

    @property
    def expected(self):
        return list(reversed(self.pattern)) if self.style == "reverse" else self.pattern

    @property
    def flash(self):
        return {"Slow": 1.0, "Normal": .65, "Fast": .35}[self.settings.playback] if self.mode == "practice" else self.rule["flash"]

    @property
    def gap(self):
        return .2 if self.mode == "practice" else self.rule["gap"]

    @property
    def preview_duration(self):
        if self.style == "pattern":
            return .4 + 1.5 + self.length * .3 + .3
        return .4 + self.length * (self.flash + self.gap) + .3

    @property
    def recall_limit(self):
        return None if self.mode == "practice" else self.rule["recall"] + self.length * 1.2

    def _begin_round(self):
        if self.mode == "practice":
            self.grid = self.settings.grid
            self.length = min(self.settings.length, self.grid * self.grid)
        else:
            self.grid = min(6, self.rule["grid"] + self.rounds_correct // 3)
            self.length = min(20, self.grid * self.grid, self.rule["length"] + self.rounds_correct)
        self.pattern = self.rng.sample(range(self.grid * self.grid), self.length)
        self.selected = []
        self.wrong_tile = None
        self.phase = "preview"
        self.phase_elapsed = 0.0
        self.feedback = ""

    def lit_tiles(self):
        if self.phase == "feedback":
            return set(self.pattern)
        if self.phase != "preview":
            return set()
        t = self.phase_elapsed - .4
        if t < 0:
            return set()
        if self.style == "pattern":
            return set(self.pattern) if t < 1.5 + self.length * .3 else set()
        index = int(t / (self.flash + self.gap))
        within = t % (self.flash + self.gap)
        return {self.pattern[index]} if index < self.length and within < self.flash else set()

    def update(self, dt):
        if self.finished or not math.isfinite(dt) or dt <= 0:
            return
        remaining = dt
        while remaining > 1e-9 and not self.finished:
            boundary = self.preview_duration if self.phase == "preview" else self.recall_limit if self.phase == "recall" else .9
            until_phase = max(0, boundary - self.phase_elapsed) if boundary is not None else remaining
            until_end = max(0, self.duration - self.elapsed) if self.duration is not None else remaining
            step = min(remaining, until_phase, until_end)
            self.elapsed += step
            self.phase_elapsed += step
            remaining -= step
            if self.duration is not None and self.elapsed >= self.duration - 1e-9:
                self.elapsed = float(self.duration)
                self.finish("Time is up")
                break
            if boundary is not None and self.phase_elapsed >= boundary - 1e-9:
                if self.phase == "preview":
                    self.phase = "recall"
                    self.phase_elapsed = 0.0
                    self.events.append(("ready", None))
                elif self.phase == "recall":
                    self._fail("Recall timed out", timeout=True)
                elif self.pending_finish:
                    self.finish("Out of lives")
                else:
                    self._begin_round()
            elif step <= 1e-12:
                break

    def select(self, tile, button=1):
        if self.finished or self.phase != "recall" or button != 1 or type(tile) is not int or not 0 <= tile < self.grid * self.grid or tile in self.selected:
            return None
        self.selections += 1
        correct = tile in self.pattern if self.style == "pattern" else tile == self.expected[len(self.selected)]
        self.selected.append(tile)
        if not correct:
            self.wrong_tile = tile
            self._fail("Wrong location" if self.style == "pattern" else "Wrong order")
            return False
        self.correct_selections += 1
        self.events.append(("correct", tile))
        if len(self.selected) == self.length:
            self.rounds_correct += 1
            self.longest = max(self.longest, self.length)
            self.streak += 1
            self.best_streak = max(self.best_streak, self.streak)
            self.recall_sum += self.phase_elapsed
            speed_bonus = round(100 * max(0, 1 - self.phase_elapsed / self.recall_limit)) if self.recall_limit else 0
            self.score += 100 * self.length + speed_bonus + 25 * min(8, self.streak - 1)
            self.phase = "feedback"
            self.phase_elapsed = 0.0
            self.feedback = "Pattern complete"
            self.events.append(("round", None))
        return True

    def _fail(self, reason, timeout=False):
        self.rounds_failed += 1
        self.timeouts += int(timeout)
        self.mistakes += int(not timeout)
        self.streak = 0
        if self.lives is not None:
            self.lives = max(0, self.lives - 1)
            self.pending_finish = self.lives == 0
        self.phase = "feedback"
        self.phase_elapsed = 0.0
        self.feedback = reason
        self.events.append(("mistake", self.wrong_tile))

    def hint(self):
        if self.mode != "practice" or self.phase != "recall" or self.finished:
            return False
        self.hints += 1
        self.assisted = True
        self.selected = []
        self.phase = "preview"
        self.phase_elapsed = 0.0
        self.events.append(("hint", None))
        return True

    def finish(self, reason="Ended early"):
        self.finished = True
        self.reason = reason

    def summary(self):
        return {"version": "2.0.0", "mode": self.mode, "difficulty": self.settings.difficulty,
                "duration": self.duration, "elapsed": round(self.elapsed, 3), "score": self.score,
                "rounds_correct": self.rounds_correct, "rounds_failed": self.rounds_failed,
                "selections": self.selections, "correct_selections": self.correct_selections,
                "accuracy": round(self.accuracy, 2), "mistakes": self.mistakes, "timeouts": self.timeouts,
                "longest": self.longest, "best_streak": self.best_streak,
                "average_recall_ms": round(self.recall_sum / self.rounds_correct * 1000, 1) if self.rounds_correct else None,
                "hints": self.hints, "assisted": self.assisted, "seed": self.seed,
                "daily": self.daily, "challenge_date": self.challenge_date, "reason": self.reason}


def board_key(row):
    mode = "daily:" + str(row.get("challenge_date") or row.get("date", "")[:10]) if row.get("daily") else row["mode"]
    return f"{mode}:{row['difficulty']}:{row.get('duration')}"


def eligible(row):
    return row.get("mode") != "practice" and not row.get("assisted") and row.get("reason") in ("Out of lives", "Time is up") and row.get("score", 0) > 0


ACHIEVEMENTS = {
    "first": ("First spark", "Complete your first round."),
    "sequence": ("Seven in mind", "Recall a seven-tile sequence."),
    "accurate": ("Clear thinking", "90% accuracy with 30 selections."),
    "reverse": ("A different angle", "Complete 5 Reverse rounds in one run."),
    "daily": ("Daily ritual", "Finish a daily run with a completed round."),
    "streak": ("In the rhythm", "Complete 5 rounds without a mistake."),
    "regular": ("Keep growing", "Save 10 sessions."),
}


def achievements(rows):
    result = set()
    for row in rows:
        if row.get("rounds_correct", 0) > 0: result.add("first")
        if row.get("longest", 0) >= 7: result.add("sequence")
        if row.get("selections", 0) >= 30 and row.get("accuracy", 0) >= 90: result.add("accurate")
        if row.get("mode") == "reverse" and row.get("rounds_correct", 0) >= 5: result.add("reverse")
        if row.get("daily") and row.get("reason") == "Time is up" and row.get("rounds_correct", 0): result.add("daily")
        if row.get("best_streak", 0) >= 5: result.add("streak")
    if len(rows) >= 10: result.add("regular")
    return result
