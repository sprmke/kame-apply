"""Generate a VAPID keypair for web push.

Usage:
    uv run python scripts/dev/generate-vapid-keys.py [--out-dir DIR]

Prints the base64url public key (VAPID_PUBLIC_KEY) and the PKCS8 PEM private key
(VAPID_PRIVATE_KEY). With --out-dir it writes vapid_private.pem and vapid_public.txt
so the API can read the private key from a path on the host.
"""

from __future__ import annotations

import argparse
import base64
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=None)
    args = parser.parse_args()

    key = ec.generate_private_key(ec.SECP256R1())
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("ascii")
    public_raw = key.public_key().public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )
    public_b64 = base64.urlsafe_b64encode(public_raw).rstrip(b"=").decode("ascii")

    if args.out_dir:
        out = args.out_dir.expanduser().resolve()
        out.mkdir(parents=True, exist_ok=True)
        private_path = out / "vapid_private.pem"
        private_path.write_text(private_pem)
        private_path.chmod(0o600)
        (out / "vapid_public.txt").write_text(public_b64 + "\n")
        print(f"Wrote {out / 'vapid_private.pem'} (keep it private)")
        print(f"Wrote {out / 'vapid_public.txt'}")

    print("\nVAPID_PUBLIC_KEY:")
    print(public_b64)
    print("\nVAPID_PRIVATE_KEY (PEM; set the env var to this value or to the file path):")
    print(private_pem, end="")


if __name__ == "__main__":
    main()
