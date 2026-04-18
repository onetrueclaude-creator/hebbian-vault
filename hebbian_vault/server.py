"""Hebbian Vault MCP Server — intelligent, use-adaptive search for Obsidian vaults."""
import json
import os
from mcp.server.fastmcp import FastMCP

from .config import Config
from .indexer import VaultIndex
from .tracker import HebbianTracker
from .rankers.bm25 import BM25Ranker
from .rankers.pagerank import PageRankRanker
from .rankers.fusion import reciprocal_rank_fusion
from .health import check_health

_index: VaultIndex | None = None
_tracker: HebbianTracker | None = None
_bm25: BM25Ranker | None = None
_pr: PageRankRanker | None = None
_config: Config | None = None
_initialized: bool = False

mcp_server = FastMCP(
    "hebbian-vault",
    instructions="Intelligent search for Obsidian vaults. Uses Hebbian learning (files you use rank higher), "
    "PageRank (hub pages surface first), and BM25 (keyword relevance) merged via Reciprocal Rank Fusion. "
    "Your vault gets smarter the more you use it. "
    "If the server starts without a vault path, use the configure_vault tool first to point it at your vault.",
)


def init_engine(vault_path: str, inline_tracking: bool = False):
    global _index, _tracker, _bm25, _pr, _config, _initialized
    _config = Config.load(vault_path)
    _config.vault_path = vault_path
    _config.inline_tracking = inline_tracking
    os.makedirs(_config.hebbian_dir(), exist_ok=True)
    _config.save()

    _index = VaultIndex(vault_path, _config.excluded_patterns)
    count = _index.scan()

    _tracker = HebbianTracker(_config)
    _tracker.import_from_frontmatter(_index.notes)

    _bm25 = BM25Ranker()
    _bm25.build_index(_index.all_bodies())

    _pr = PageRankRanker()
    _pr.build_graph(_index.link_graph())
    _pr.compute_global()

    _initialized = True
    return count


def _not_ready() -> str:
    return json.dumps({
        "error": "No vault configured. Use the configure_vault tool first to point the server at your Obsidian vault.",
        "hint": "Call configure_vault with the absolute path to your vault directory.",
    })


@mcp_server.tool(name="configure_vault", annotations={"readOnlyHint": False})
def configure_vault(vault_path: str, inline_tracking: bool = False) -> str:
    """Configure the vault path for this server. Call this first if the server
    started without a --vault argument. The vault_path must be an absolute path
    to an Obsidian vault directory containing .md files."""
    if not os.path.isdir(vault_path):
        return json.dumps({"error": f"Directory does not exist: {vault_path}"})

    count = init_engine(vault_path, inline_tracking=inline_tracking)
    return json.dumps({
        "status": "configured",
        "vault_path": vault_path,
        "notes_indexed": count,
        "inline_tracking": inline_tracking,
    }, indent=2)


@mcp_server.tool(name="vault_search", annotations={"readOnlyHint": False})
def vault_search(query: str, limit: int = 10, include_content: bool = False) -> str:
    """Search the vault with hybrid ranking. Results are ranked by keyword relevance,
    graph centrality, and usage frequency merged via Reciprocal Rank Fusion.
    Each returned result strengthens that file's future ranking (Hebbian learning)."""
    if not _initialized:
        return _not_ready()

    bm25_results = _bm25.search(query, top_k=50)
    seed_docs = [doc for doc, _ in bm25_results[:10]]
    ppr_results = _pr.personalized_search(seed_docs, top_k=50)

    hebbian_ranked = []
    for rel in _index.all_rel_paths():
        score = _tracker.usage_score(rel)
        if score > 0:
            hebbian_ranked.append((rel, score))
    hebbian_ranked.sort(key=lambda x: -x[1])

    ranked_lists = [bm25_results, ppr_results, hebbian_ranked]
    merged = reciprocal_rank_fusion(ranked_lists, top_n=limit)

    results = []
    for rel_path, rrf_score in merged:
        note = _index.get_note(rel_path)
        if not note:
            continue
        _tracker.strengthen(rel_path)

        snippet = note.body[:200].replace("\n", " ").strip()
        entry = {
            "path": rel_path,
            "title": note.title,
            "score": round(rrf_score, 6),
            "snippet": snippet,
            "retrieval_count": _tracker.get_count(rel_path),
            "pagerank": round(_pr.get_score(rel_path), 6),
        }
        if include_content:
            entry["content"] = note.body
        results.append(entry)

    return json.dumps({
        "results": results,
        "total_matches": len(merged),
        "query": query,
    }, indent=2)


@mcp_server.tool(name="vault_read", annotations={"readOnlyHint": False})
def vault_read(path: str) -> str:
    """Read a single vault note by relative path. Returns full content with parsed
    frontmatter, outgoing links, and incoming links. Strengthens the file's Hebbian score."""
    if not _initialized:
        return _not_ready()

    note = _index.get_note(path)
    if not note:
        stem = path.replace(".md", "").split("/")[-1]
        note = _index.find_by_stem(stem)
    if not note:
        return json.dumps({"error": f"Note not found: {path}"})

    _tracker.strengthen(note.rel_path)

    return json.dumps({
        "path": note.rel_path,
        "title": note.title,
        "frontmatter": note.frontmatter,
        "content": note.body,
        "outgoing_links": note.outgoing_links,
        "incoming_links": note.incoming_links,
        "retrieval_count": _tracker.get_count(note.rel_path),
        "pagerank": round(_pr.get_score(note.rel_path), 6),
    }, indent=2)


@mcp_server.tool(name="vault_neighbors", annotations={"readOnlyHint": True})
def vault_neighbors(path: str, depth: int = 1, limit: int = 20) -> str:
    """Find notes connected to a given note by wikilinks. Shows both outgoing and
    incoming links, with PageRank scores for prioritization."""
    if not _initialized:
        return _not_ready()

    note = _index.get_note(path)
    if not note:
        stem = path.replace(".md", "").split("/")[-1]
        note = _index.find_by_stem(stem)
    if not note:
        return json.dumps({"error": f"Note not found: {path}"})

    neighbors = []
    seen = {note.rel_path}

    for target_stem in note.outgoing_links:
        target_rel = _index.stem_to_path.get(target_stem)
        if target_rel and target_rel not in seen:
            neighbors.append({
                "path": target_rel,
                "direction": "outgoing",
                "pagerank": round(_pr.get_score(target_rel), 6),
            })
            seen.add(target_rel)

    for source_rel in note.incoming_links:
        if source_rel not in seen:
            neighbors.append({
                "path": source_rel,
                "direction": "incoming",
                "pagerank": round(_pr.get_score(source_rel), 6),
            })
            seen.add(source_rel)

    if depth >= 2:
        hop1_paths = [n["path"] for n in neighbors]
        for h1_path in hop1_paths:
            h1_note = _index.get_note(h1_path)
            if not h1_note:
                continue
            for stem in h1_note.outgoing_links:
                rel = _index.stem_to_path.get(stem)
                if rel and rel not in seen:
                    neighbors.append({"path": rel, "direction": "2-hop", "pagerank": round(_pr.get_score(rel), 6)})
                    seen.add(rel)

    neighbors.sort(key=lambda n: -n["pagerank"])
    return json.dumps({
        "center": note.rel_path,
        "neighbors": neighbors[:limit],
        "total": len(neighbors),
    }, indent=2)


@mcp_server.tool(name="vault_hot", annotations={"readOnlyHint": True})
def vault_hot(limit: int = 20) -> str:
    """Top-N most-used files by Hebbian score (usage frequency weighted by recency).
    Shows what the vault considers most important based on actual usage patterns."""
    if not _initialized:
        return _not_ready()

    scored = []
    for rel in _index.all_rel_paths():
        usage = _tracker.usage_score(rel)
        scored.append({
            "path": rel,
            "usage_score": round(usage, 4),
            "retrieval_count": _tracker.get_count(rel),
            "pagerank": round(_pr.get_score(rel), 6),
            "last_accessed": _tracker.get_last_accessed(rel),
        })

    scored.sort(key=lambda x: -x["usage_score"])
    return json.dumps({"files": scored[:limit]}, indent=2)


@mcp_server.tool(name="vault_stats", annotations={"readOnlyHint": True})
def vault_stats() -> str:
    """Vault-level analytics: file count, link count, orphans, broken links,
    average connectivity, and top hub pages by PageRank."""
    if not _initialized:
        return _not_ready()

    graph = _index.link_graph()
    total_links = sum(len(targets) for targets in graph.values())
    orphans = sum(1 for n in _index.notes.values() if not n.incoming_links and not n.outgoing_links)
    broken = sum(
        1 for n in _index.notes.values()
        for stem in n.outgoing_links
        if stem not in _index.stem_to_path
    )

    top_hubs = sorted(_pr.scores.items(), key=lambda kv: -kv[1])[:10]

    return json.dumps({
        "total_files": len(_index.notes),
        "total_links": total_links,
        "orphan_count": orphans,
        "broken_link_count": broken,
        "avg_links_per_file": round(total_links / max(len(_index.notes), 1), 2),
        "top_hubs": [{"path": p, "pagerank": round(s, 6)} for p, s in top_hubs],
    }, indent=2)


@mcp_server.tool(name="vault_health", annotations={"readOnlyHint": True})
def vault_health() -> str:
    """Structural integrity check: broken links, orphaned leaves, missing frontmatter.
    Returns a list of issues found."""
    if not _initialized:
        return _not_ready()

    issues = check_health(_index)
    return json.dumps({
        "issues": issues,
        "total": len(issues),
    }, indent=2)
