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
        choices=["stdio", "streamable-http"],
        default="stdio",
        help="MCP transport (default: stdio for local use)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for streamable-http transport (default: 8000)",
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

    mcp_server.run(transport=args.transport)


if __name__ == "__main__":
    main()
