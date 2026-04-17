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
        required=True,
        help="Path to the Obsidian vault directory",
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

    vault_path = os.path.expanduser(args.vault)
    if not os.path.isdir(vault_path):
        print(f"Error: vault path does not exist: {vault_path}", file=sys.stderr)
        sys.exit(1)

    from .server import mcp_server, init_engine
    from .config import Config

    count = init_engine(vault_path)
    print(f"hebbian-vault: indexed {count} notes in {vault_path}", file=sys.stderr)

    if args.inline_tracking:
        from .server import _config
        if _config:
            _config.inline_tracking = True
            _config.save()

    mcp_server.run(transport=args.transport)


if __name__ == "__main__":
    main()
