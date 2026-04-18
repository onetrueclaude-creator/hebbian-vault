"""Vault indexer — scans markdown files, parses frontmatter, extracts wikilinks, builds search index."""
import os
import re
import fnmatch
from dataclasses import dataclass, field

import yaml


@dataclass
class VaultNote:
    path: str
    rel_path: str
    title: str
    content: str
    body: str
    frontmatter: dict = field(default_factory=dict)
    outgoing_links: list[str] = field(default_factory=list)
    incoming_links: list[str] = field(default_factory=list)


WIKILINK_RE = re.compile(r"\[\[([^\]|]+?)(?:\|[^\]]+?)?\]\]")
CODE_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")


def _strip_code(text: str) -> str:
    text = CODE_FENCE_RE.sub("", text)
    text = INLINE_CODE_RE.sub("", text)
    return text


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    if not content.startswith("---"):
        return {}, content
    end = content.find("---", 3)
    if end == -1:
        return {}, content
    fm_text = content[3:end]
    body = content[end + 3:].lstrip("\n")
    try:
        fm = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError:
        fm = {}
    return fm, body


def _extract_wikilinks(body: str) -> list[str]:
    cleaned = _strip_code(body)
    links = []
    for m in WIKILINK_RE.finditer(cleaned):
        target = m.group(1).strip()
        stem = target.split("/")[-1].replace(".md", "")
        if stem and "NNN" not in stem and "CANDIDATE" not in stem:
            links.append(stem)
    return list(set(links))


def _matches_excluded(rel_path: str, patterns: list[str]) -> bool:
    for pattern in patterns:
        if fnmatch.fnmatch(rel_path, pattern):
            return True
    return False


class VaultIndex:
    def __init__(self, vault_path: str, excluded_patterns: list[str] | None = None):
        self.vault_path = vault_path
        self.excluded = excluded_patterns or []
        self.notes: dict[str, VaultNote] = {}
        self.stem_to_path: dict[str, str] = {}

    def scan(self) -> int:
        self.notes.clear()
        self.stem_to_path.clear()

        for root, _, files in os.walk(self.vault_path):
            for fname in files:
                if not fname.endswith(".md"):
                    continue
                full_path = os.path.join(root, fname)
                rel = os.path.relpath(full_path, self.vault_path)

                if _matches_excluded(rel, self.excluded):
                    continue

                try:
                    with open(full_path, encoding="utf-8") as f:
                        content = f.read()
                except (FileNotFoundError, PermissionError, UnicodeDecodeError):
                    continue

                fm, body = _parse_frontmatter(content)
                title = fm.get("title") or fname.replace(".md", "")
                outgoing = _extract_wikilinks(body)

                stem = fname.replace(".md", "")
                self.stem_to_path[stem] = rel

                note = VaultNote(
                    path=full_path,
                    rel_path=rel,
                    title=title,
                    content=content,
                    body=body,
                    frontmatter=fm,
                    outgoing_links=outgoing,
                )
                self.notes[rel] = note

        self._resolve_incoming()
        return len(self.notes)

    def _resolve_incoming(self):
        for note in self.notes.values():
            note.incoming_links = []

        for source_rel, note in self.notes.items():
            for target_stem in note.outgoing_links:
                target_rel = self.stem_to_path.get(target_stem)
                if target_rel and target_rel in self.notes:
                    self.notes[target_rel].incoming_links.append(source_rel)

    def get_note(self, rel_path: str) -> VaultNote | None:
        return self.notes.get(rel_path)

    def find_by_stem(self, stem: str) -> VaultNote | None:
        rel = self.stem_to_path.get(stem)
        return self.notes.get(rel) if rel else None

    def all_rel_paths(self) -> list[str]:
        return list(self.notes.keys())

    def all_bodies(self) -> dict[str, str]:
        return {rel: n.body for rel, n in self.notes.items()}

    def link_graph(self) -> dict[str, set[str]]:
        graph = {}
        for rel, note in self.notes.items():
            targets = set()
            for stem in note.outgoing_links:
                target_rel = self.stem_to_path.get(stem)
                if target_rel and target_rel != rel:
                    targets.add(target_rel)
            graph[rel] = targets
        return graph
