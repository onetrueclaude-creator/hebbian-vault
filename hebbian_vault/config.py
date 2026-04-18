"""Configuration management for hebbian-vault."""
import json
import os
from dataclasses import dataclass, field


@dataclass
class Config:
    vault_path: str = ""
    inline_tracking: bool = False
    recency_boost: bool = False
    decay_rate: float = 0.03
    index_on_startup: bool = True
    reindex_interval_minutes: int = 30
    excluded_patterns: list[str] = field(default_factory=lambda: [
        "templates/*", ".obsidian/*", ".trash/*", ".hebbian/*",
    ])

    def hebbian_dir(self) -> str:
        return os.path.join(self.vault_path, ".hebbian")

    def tracking_path(self) -> str:
        return os.path.join(self.hebbian_dir(), "tracking.json")

    def pagerank_path(self) -> str:
        return os.path.join(self.hebbian_dir(), "pagerank.json")

    def graph_path(self) -> str:
        return os.path.join(self.hebbian_dir(), "graph.json")

    def config_path(self) -> str:
        return os.path.join(self.hebbian_dir(), "config.json")

    def save(self):
        os.makedirs(self.hebbian_dir(), exist_ok=True)
        with open(self.config_path(), "w") as f:
            json.dump({
                "vault_path": self.vault_path,
                "inline_tracking": self.inline_tracking,
                "recency_boost": self.recency_boost,
                "decay_rate": self.decay_rate,
                "index_on_startup": self.index_on_startup,
                "reindex_interval_minutes": self.reindex_interval_minutes,
                "excluded_patterns": self.excluded_patterns,
            }, f, indent=2)

    @classmethod
    def load(cls, vault_path: str) -> "Config":
        config_path = os.path.join(vault_path, ".hebbian", "config.json")
        cfg = cls(vault_path=vault_path)
        if os.path.exists(config_path):
            with open(config_path) as f:
                data = json.load(f)
            for k, v in data.items():
                if hasattr(cfg, k):
                    setattr(cfg, k, v)
            cfg.vault_path = vault_path
        return cfg
