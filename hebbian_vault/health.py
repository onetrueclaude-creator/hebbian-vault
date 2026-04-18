"""Vault structural health checks."""
from .indexer import VaultIndex


def check_health(index: VaultIndex) -> list[dict]:
    issues = []
    for rel, note in index.notes.items():
        for target_stem in note.outgoing_links:
            if target_stem not in index.stem_to_path:
                issues.append({"file": rel, "type": "broken_link", "detail": f"[[{target_stem}]] does not resolve"})

        if not note.frontmatter:
            issues.append({"file": rel, "type": "missing_frontmatter", "detail": "no YAML frontmatter"})

        if note.frontmatter and not note.incoming_links:
            ftype = note.frontmatter.get("type", "")
            if ftype == "leaf":
                issues.append({"file": rel, "type": "orphaned_leaf", "detail": "no incoming links from any file"})

    return issues
