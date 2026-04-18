"""Hebbian tracker — manages retrieval_count and last_accessed for vault files."""
import json
import os
import re
import math
from datetime import datetime, timezone, timedelta
from .config import Config


class HebbianTracker:
    def __init__(self, config: Config):
        self.config = config
        self.data: dict[str, dict] = {}
        self._load()

    def _load(self):
        path = self.config.tracking_path()
        if os.path.exists(path):
            with open(path) as f:
                self.data = json.load(f)

    def _save(self):
        os.makedirs(self.config.hebbian_dir(), exist_ok=True)
        with open(self.config.tracking_path(), "w") as f:
            json.dump(self.data, f, indent=2)

    def strengthen(self, rel_path: str):
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        if rel_path not in self.data:
            self.data[rel_path] = {"retrieval_count": 0, "last_accessed": now}
        self.data[rel_path]["retrieval_count"] += 1
        self.data[rel_path]["last_accessed"] = now

        if self.config.inline_tracking:
            self._write_inline(rel_path)

        self._save()

    def _write_inline(self, rel_path: str):
        full_path = os.path.join(self.config.vault_path, rel_path)
        try:
            with open(full_path, encoding="utf-8") as f:
                content = f.read()
        except (FileNotFoundError, PermissionError):
            return

        if not content.startswith("---"):
            return

        entry = self.data[rel_path]
        rc = entry["retrieval_count"]
        la = entry["last_accessed"]

        if "retrieval_count:" in content:
            content = re.sub(r"^retrieval_count:.*$", f"retrieval_count: {rc}", content, count=1, flags=re.MULTILINE)
        else:
            end = content.find("---", 3)
            if end > 0:
                insert = content.rfind("\n", 0, end)
                if insert > 0:
                    content = content[:insert] + f"\nretrieval_count: {rc}" + content[insert:]

        if "last_accessed:" in content:
            content = re.sub(r"^last_accessed:.*$", f"last_accessed: {la}", content, count=1, flags=re.MULTILINE)

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

    def get_count(self, rel_path: str) -> int:
        entry = self.data.get(rel_path, {})
        return entry.get("retrieval_count", 0)

    def get_last_accessed(self, rel_path: str) -> str:
        entry = self.data.get(rel_path, {})
        return entry.get("last_accessed", "")

    def usage_score(self, rel_path: str) -> float:
        rc = self.get_count(rel_path)
        if rc == 0:
            return 0.0
        la = self.get_last_accessed(rel_path)
        if not la:
            return math.log(1 + rc)
        try:
            last = datetime.fromisoformat(la.replace("Z", "+00:00"))
            days_ago = (datetime.now(timezone.utc) - last).total_seconds() / 86400
        except (ValueError, TypeError):
            days_ago = 30
        decay = math.exp(-self.config.decay_rate * days_ago)
        return math.log(1 + rc) * decay

    def import_from_frontmatter(self, notes: dict):
        for rel_path, note in notes.items():
            fm = note.frontmatter if hasattr(note, "frontmatter") else note
            rc = fm.get("retrieval_count", 0)
            la = fm.get("last_retrieved") or fm.get("last_accessed", "")
            if rc or la:
                if rel_path not in self.data:
                    self.data[rel_path] = {}
                if rc:
                    self.data[rel_path]["retrieval_count"] = int(float(rc))
                if la:
                    self.data[rel_path]["last_accessed"] = str(la)
        self._save()
