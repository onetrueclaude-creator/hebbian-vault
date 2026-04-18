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
        help="[Pro] Write retrieval_count directly into file frontmatter (default: sidecar .hebbian/ directory)",
    )
    parser.add_argument(
        "--license-key",
        default=None,
        help="Pro license key (JWT). Overrides HEBBIAN_VAULT_LICENSE env var and ~/.hebbian-vault/license.jwt",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http", "sse"],
        default="stdio",
        help="MCP transport (default: stdio — the right choice for MCPize proxy mode and local Claude Desktop)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for streamable-http transport (default: 8000, ignored for stdio)",
    )
    args = parser.parse_args()

    from .license import load_license, feature_gate
    license = load_license(args.license_key)

    inline_tracking = False
    if args.inline_tracking:
        if feature_gate(license, "inline_tracking"):
            inline_tracking = True

    from .server import mcp_server, init_engine

    if args.vault:
        vault_path = os.path.expanduser(args.vault)
        if not os.path.isdir(vault_path):
            print(f"Error: vault path does not exist: {vault_path}", file=sys.stderr)
            sys.exit(1)
        count = init_engine(vault_path, inline_tracking=inline_tracking)
        print(f"hebbian-vault: indexed {count} notes in {vault_path}", file=sys.stderr)
    else:
        print("hebbian-vault: starting without vault (use configure_vault tool to set path)", file=sys.stderr)

    if license:
        print(f"hebbian-vault: Pro license active (plan={license.plan}, sub={license.subject})",
              file=sys.stderr)

    if args.transport in ("streamable-http", "sse"):
        port = int(os.environ.get("PORT") or args.port)
        mcp_server.settings.host = "0.0.0.0"
        mcp_server.settings.port = port
        mcp_server.settings.stateless_http = True
        print(f"hebbian-vault: binding {args.transport} on 0.0.0.0:{port} (stateless)", file=sys.stderr)

    mcp_server.run(transport=args.transport)


if __name__ == "__main__":
    main()
