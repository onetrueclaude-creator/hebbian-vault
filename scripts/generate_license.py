#!/usr/bin/env python3
"""Issue a hebbian-vault Pro license.

Usage:
    python scripts/generate_license.py --email buyer@example.com --plan lifetime
    python scripts/generate_license.py --email buyer@example.com --plan pro --days 365

The private signing key is expected at ~/.hebbian-vault/signing_key.pem
(generated once, chmod 600, never committed, never shared).

The output JWT is what you paste into the email to the customer. They install
it via --license-key or HEBBIAN_VAULT_LICENSE env var.
"""
from __future__ import annotations

import argparse
import json
import secrets
import sys
import time
from pathlib import Path

import jwt
from cryptography.hazmat.primitives import serialization


PRIVATE_KEY_PATH = Path.home() / ".hebbian-vault" / "signing_key.pem"
ISSUER = "hebbian-vault"
ALGORITHM = "EdDSA"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True, help="Customer email (goes into 'sub' claim)")
    parser.add_argument(
        "--plan",
        choices=["pro", "lifetime"],
        default="lifetime",
        help="License plan. 'lifetime' has no expiry; 'pro' has --days expiry.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="Days until expiry (ignored for lifetime). Default for 'pro': 365.",
    )
    parser.add_argument(
        "--features",
        default="all",
        help="Comma-separated feature list. 'all' unlocks everything. Default: all",
    )
    parser.add_argument(
        "--key",
        default=str(PRIVATE_KEY_PATH),
        help=f"Path to Ed25519 private key PEM (default: {PRIVATE_KEY_PATH})",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Print only the JWT (for scripting). Skips the email template preview.",
    )
    args = parser.parse_args()

    key_path = Path(args.key).expanduser()
    if not key_path.is_file():
        print(f"error: private key not found at {key_path}", file=sys.stderr)
        print("Run the key-generation snippet from the v0.2.0 release notes first.", file=sys.stderr)
        return 1

    private_key = serialization.load_pem_private_key(key_path.read_bytes(), password=None)

    now = int(time.time())
    claims: dict = {
        "iss": ISSUER,
        "sub": args.email,
        "plan": args.plan,
        "iat": now,
        "jti": secrets.token_hex(8),
        "features": [f.strip() for f in args.features.split(",") if f.strip()],
    }
    if args.plan == "pro":
        days = args.days if args.days is not None else 365
        claims["exp"] = now + days * 86400

    token = jwt.encode(claims, private_key, algorithm=ALGORITHM)

    if args.quiet:
        print(token)
        return 0

    print("=" * 60)
    print("LICENSE GENERATED")
    print("=" * 60)
    print(f"Buyer:    {args.email}")
    print(f"Plan:     {args.plan}")
    if "exp" in claims:
        import datetime as dt
        print(f"Expires:  {dt.datetime.fromtimestamp(claims['exp']).isoformat()}")
    print(f"Features: {', '.join(claims['features'])}")
    print(f"JTI:      {claims['jti']}")
    print()
    print("--- LICENSE JWT (send this to the customer) ---")
    print(token)
    print()
    print("--- EMAIL TEMPLATE ---")
    print(f"""To: {args.email}
Subject: Your hebbian-vault Pro license

Thanks for supporting hebbian-vault. Your license key is below.

Install in any ONE of three ways:

  1. Environment variable:
       export HEBBIAN_VAULT_LICENSE="{token}"

  2. CLI flag:
       hebbian-vault --license-key "{token}" --vault ~/my-vault

  3. Config file:
       echo "{token}" > ~/.hebbian-vault/license.jwt

Any one is enough. Pro features unlock automatically on the next launch.

Questions or issues? Reply to this email.
""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
