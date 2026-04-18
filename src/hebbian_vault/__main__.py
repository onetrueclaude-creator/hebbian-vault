"""CLI entry point for hebbian-vault MCP server."""
import argparse
import sys
import os

def main():
    parser = argparse.ArgumentParser(
        prog="hebbian-vault",
        description="MCP server for intelligent, use-adaptive Obsidian vault search.",
    )
    parser.add_argument(
        "--vault", "-v",
        default=None,
        help="Path to the Obsidian vault directory (optional — can be configured later via configure_vault tool)",
    )
    parser.add_argument(
        "--inline-tracking",
        action="store_true",
        help="Write retrieval_count directly into file frontmatter (default: sidecar .hebbian/ directory)",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http", "sse"],
        default=None,
        help="MCP transport (default: auto-detect from environment)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port for HTTP transport (default: from PORT env var or 8000)",
    )
    args = parser.parse_args()

    from .server import mcp_server, init_engine

    if args.vault:
        vault_path = os.path.expanduser(args.vault)
        if not os.path.isdir(vault_path):
            print(f"Error: vault path does not exist: {vault_path}", file=sys.stderr)
            sys.exit(1)
        count = init_engine(vault_path, inline_tracking=args.inline_tracking)
        print(f"hebbian-vault: indexed {count} notes in {vault_path}", file=sys.stderr)
    else:
        print("hebbian-vault: starting without vault (use configure_vault tool to set path)", file=sys.stderr)

    # Auto-detect transport: if PORT env var is set (Cloud Run / MCPize), use HTTP
    transport = args.transport
    if transport is None:
        if os.environ.get("PORT"):
            transport = "streamable-http"
            print(f"hebbian-vault: PORT={os.environ['PORT']} detected, using streamable-http transport", file=sys.stderr)
        else:
            transport = "stdio"

    # Use PORT env var if set (Cloud Run injects this)
    port = args.port or int(os.environ.get("PORT", "8000"))

    if transport in ("streamable-http", "sse"):
        # Set host to 0.0.0.0 for container environments
        os.environ.setdefault("UVICORN_HOST", "0.0.0.0")
        os.environ.setdefault("UVICORN_PORT", str(port))

    mcp_server.run(transport=transport)


if __name__ == "__main__":
    main()
