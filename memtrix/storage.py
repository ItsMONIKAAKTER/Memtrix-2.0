"""Validated, atomic profile saves and explicitly separated v1 score imports."""
import csv
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import tempfile
import uuid
from .model import Settings, MODES, RULES, board_key, eligible


def data_directory():
    if os.environ.get("MEMTRIX_DATA"):
        return Path(os.environ["MEMTRIX_DATA"]).expanduser()
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Memtrix"
    return Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))) / "memtrix"


def profile():
    return {"settings": {}, "sessions": [], "legacy_scores": {}}


def valid_row(row):
    if not isinstance(row, dict) or not isinstance(row.get("mode"), str) or row["mode"] not in MODES:
        return False
    if not isinstance(row.get("difficulty"), str) or row["difficulty"] not in RULES or row.get("duration") not in (None, 60, 90, 120):
        return False
    for key in ("score", "elapsed", "accuracy", "rounds_correct", "rounds_failed", "selections", "correct_selections", "mistakes", "timeouts", "longest", "best_streak", "hints"):
        value = row.get(key)
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 10**12:
            return False
    if row["accuracy"] > 100 or type(row.get("daily")) is not bool or type(row.get("assisted")) is not bool:
        return False
    if not isinstance(row.get("reason"), str) or not isinstance(row.get("date"), str):
        return False
    delay = row.get("average_recall_ms")
    if delay is not None and (type(delay) not in (int, float) or not math.isfinite(delay) or delay < 0):
        return False
    try:
        datetime.fromisoformat(row["date"])
    except ValueError:
        return False
    return True


def normalize_legacy(raw):
    if not isinstance(raw, dict):
        raise ValueError("The legacy file must contain a difficulty-to-score object.")
    result = {}
    for key, value in raw.items():
        name = str(key).strip().capitalize()
        if name in RULES and type(value) is int and 0 <= value <= 10**9:
            result[name] = max(result.get(name, 0), value)
    if not result:
        raise ValueError("No valid Easy, Medium or Hard v1 scores were found.")
    return result


class Store:
    def __init__(self, directory=None):
        self.directory = Path(directory) if directory is not None else data_directory()
        self.path = self.directory / "progress.json"
        self.data = {"schema": 2, "active": "Player", "profiles": {"Player": profile()}}
        self.notice = ""
        self.load()

    def load(self):
        if not self.path.exists(): return
        try:
            # Allow the documented 20 profiles × 1,000 normal session records.
            if self.path.stat().st_size > 64_000_000: raise ValueError("Oversized file")
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict) or raw.get("schema") != 2 or not isinstance(raw.get("profiles"), dict):
                raise ValueError("Unknown save schema")
            profiles = {}
            for name, data in list(raw["profiles"].items())[:20]:
                if not isinstance(name, str) or not 1 <= len(name) <= 24 or not name.isprintable() or not isinstance(data, dict): continue
                rows = data.get("sessions", [])
                rows = [r for r in rows[-1000:] if valid_row(r)] if isinstance(rows, list) else []
                try: legacy = normalize_legacy(data.get("legacy_scores", {}))
                except ValueError: legacy = {}
                profiles[name] = {"settings": vars(Settings.from_dict(data.get("settings"))), "sessions": rows, "legacy_scores": legacy}
            if not profiles: raise ValueError("No valid profiles")
            active = raw.get("active")
            self.data = {"schema": 2, "profiles": profiles, "active": active if isinstance(active, str) and active in profiles else next(iter(profiles))}
        except (OSError, ValueError, TypeError):
            try:
                backup = self.directory / f"progress-recovery-{uuid.uuid4().hex[:8]}.json"
                backup.write_bytes(self.path.read_bytes())
                self.notice = "Unreadable progress preserved as a recovery file. A fresh profile is ready."
            except OSError:
                self.notice = "Progress could not be read. Using a temporary profile."

    @property
    def active(self): return self.data["active"]

    @property
    def current(self): return self.data["profiles"][self.active]

    @property
    def sessions(self): return self.current["sessions"]

    @property
    def settings(self): return Settings.from_dict(self.current["settings"])

    def save(self):
        temporary = None
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            fd, temporary = tempfile.mkstemp(prefix="progress-", suffix=".tmp", dir=self.directory)
            with os.fdopen(fd, "w", encoding="utf-8") as file:
                json.dump(self.data, file, ensure_ascii=False, indent=2, allow_nan=False)
                file.flush(); os.fsync(file.fileno())
            os.replace(temporary, self.path)
            return True
        except (OSError, ValueError):
            self.notice = "Save folder is not writable. This visit's progress remains in memory."
            return False
        finally:
            if temporary:
                try: Path(temporary).unlink(missing_ok=True)
                except OSError: pass

    def create(self, name):
        name = " ".join(name.split())
        if not 1 <= len(name) <= 24 or not name.isprintable(): raise ValueError("Use 1–24 readable characters.")
        if any(n.casefold() == name.casefold() for n in self.data["profiles"]): raise ValueError("That profile already exists.")
        if len(self.data["profiles"]) >= 20: raise ValueError("The profile limit is 20.")
        self.data["profiles"][name] = profile(); self.data["active"] = name
        return self.save()

    def select(self, name):
        if name not in self.data["profiles"]: raise ValueError("Unknown profile")
        self.data["active"] = name
        return self.save()

    def set_settings(self, settings):
        self.current["settings"] = vars(Settings.from_dict(vars(settings)))
        return self.save()

    def add(self, summary):
        row = {**summary, "id": uuid.uuid4().hex, "date": datetime.now(timezone.utc).isoformat()}
        previous = [r for r in self.sessions if eligible(r) and board_key(r) == board_key(row)]
        best = eligible(row) and (not previous or row["score"] > max(r["score"] for r in previous))
        self.sessions.append(row); self.current["sessions"] = self.sessions[-1000:]
        return row, best, self.save()

    def bests(self):
        result = {}
        for row in self.sessions:
            if not eligible(row): continue
            key = board_key(row)
            if key not in result or row["score"] > result[key]["score"]: result[key] = row
        return sorted(result.values(), key=lambda r: (r["mode"], r["difficulty"], r.get("duration") or 0))

    def import_legacy(self, path):
        path = Path(path)
        if path.stat().st_size > 1_000_000: raise ValueError("Legacy score file is too large.")
        values = normalize_legacy(json.loads(path.read_text(encoding="utf-8-sig")))
        for name, score in values.items():
            self.current["legacy_scores"][name] = max(self.current["legacy_scores"].get(name, 0), score)
        return self.save()

    def export(self):
        folder = self.directory / "exports"; folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"memtrix-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:4]}.csv"
        fields = ["date", "mode", "difficulty", "duration", "elapsed", "score", "accuracy", "rounds_correct", "rounds_failed", "selections", "correct_selections", "mistakes", "timeouts", "longest", "best_streak", "average_recall_ms", "hints", "assisted", "daily", "challenge_date", "seed", "reason", "version"]
        with path.open("w", encoding="utf-8-sig", newline="") as file:
            writer = csv.DictWriter(file, fields, extrasaction="ignore"); writer.writeheader()
            for row in self.sessions:
                writer.writerow({k: "'" + str(row.get(k, "")) if str(row.get(k, "")).lstrip().startswith(("=", "+", "-", "@")) else row.get(k, "") for k in fields})
        return path
