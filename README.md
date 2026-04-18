# hebbian-vault

**MCP server for intelligent, use-adaptive Obsidian vault search.**

Your vault remembers what matters. Files you use strengthen. Unused files fade. Hub pages surface first. Search gets better over time.

## What it does

Unlike standard Obsidian search (keyword matching), hebbian-vault uses four signals merged via [Reciprocal Rank Fusion](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf):

- **BM25** -- keyword relevance (like standard search, but ranked)
- **Personalized PageRank** -- graph centrality biased toward your query (hub pages surface first)
- **Hebbian usage** -- files you actually use rank higher, with recency decay
- **RRF merge** -- combines all signals without weight tuning

Works with any Obsidian vault. No cloud. No Obsidian running required. Direct filesystem access.

## Install

```bash
pip install hebbian-vault
```

## Usage

### Claude Code
```bash
claude mcp add hebbian-vault -- hebbian-vault --vault ~/my-vault
```

### Claude Desktop
Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "hebbian-vault": {
      "command": "uvx",
      "args": ["hebbian-vault", "--vault", "/path/to/vault"]
    }
  }
}
```

### Direct
```bash
hebbian-vault --vault ~/my-vault
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `configure_vault` | Point the server at a vault at runtime (if not set via `--vault`) |
| `vault_search` | Hybrid ranked search (BM25 + PageRank + Hebbian) |
| `vault_read` | Read a note with frontmatter, links, and Hebbian metadata |
| `vault_neighbors` | Find connected notes by wikilinks (1-hop or 2-hop) |
| `vault_hot` | Top-N most-used files by Hebbian score |
| `vault_stats` | Vault analytics (files, links, orphans, hubs) |
| `vault_health` | Structural integrity check (broken links, orphans) |

## How Hebbian learning works

Every time `vault_search` or `vault_read` returns a file, that file's retrieval count increments. Files accessed recently get a recency boost. Files untouched for weeks decay. Over time, the vault develops a "heat signature" -- frequently useful files strengthen, rarely useful files fade.

This is [Hebbian learning](https://en.wikipedia.org/wiki/Hebbian_theory) applied to information retrieval: "neurons that fire together wire together." Your vault adapts to how you actually use it.

## Storage

By default, tracking data is stored in a `.hebbian/` sidecar directory inside your vault. Your markdown files are not modified.

Pro users can enable `--inline-tracking` to write `retrieval_count` directly into YAML frontmatter (visible natively in Obsidian, queryable via Dataview).

## Pro tier

The free tier is fully featured for most use. Pro unlocks convenience features for power users:

- `--inline-tracking` — write retrieval counts into note frontmatter instead of sidecar files
- Priority email support from the developer
- Future premium features ship Pro-unlocked by default

License activation — any one of these works:

```bash
# 1. Environment variable (good for shell profiles)
export HEBBIAN_VAULT_LICENSE="eyJhbGc..."

# 2. CLI flag (good for one-off testing)
hebbian-vault --license-key "eyJhbGc..." --vault ~/my-vault

# 3. Config file (good for permanent install)
echo "eyJhbGc..." > ~/.hebbian-vault/license.jwt
```

Licenses are verified fully offline — no phone-home, no activation server. Get a license: **[coming soon — Dodo Payments storefront in verification]**.

## Options

```
hebbian-vault --vault PATH          Path to Obsidian vault
              --inline-tracking     [Pro] Write tracking to file frontmatter
              --license-key KEY     Pro license JWT (also reads HEBBIAN_VAULT_LICENSE env)
              --transport TYPE      stdio (default) or streamable-http
              --port PORT           Port for HTTP transport (default: 8000)
```

## Requirements

- Python 3.10+
- An Obsidian vault (any size, wikilinks recommended for graph features)

## License

MIT
