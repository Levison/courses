"""A stand-in for your real authorization server (Auth0, Entra, Keycloak, Okta...).

It only does the one thing this module needs: hold an RSA key and mint signed,
audience-bound JWT access tokens. A real AS also does login, consent, PKCE,
Client ID Metadata Documents (CIMD), and RFC 9207 `iss` in the auth response.

    python dev_issuer.py mint --scope "notes:read notes:write" --sub alice
"""

from __future__ import annotations

import argparse
import time
import uuid
from pathlib import Path

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

ISSUER = "https://auth.dev.example"  # the `iss` the resource server will insist on
RESOURCE = "http://127.0.0.1:8765/mcp"  # RFC 8707 resource indicator == our MCP endpoint
KEY_FILE = Path(__file__).with_name("dev_issuer_key.pem")  # gitignored (*.pem)


def private_key() -> rsa.RSAPrivateKey:
    if not KEY_FILE.exists():
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        KEY_FILE.write_bytes(
            key.private_bytes(
                serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
            )
        )
        KEY_FILE.chmod(0o600)
    return serialization.load_pem_private_key(KEY_FILE.read_bytes(), password=None)  # type: ignore[return-value]


def public_key_pem() -> bytes:
    return private_key().public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )


def mint(sub: str, scope: str, audience: str = RESOURCE, ttl: int = 600, client_id: str = "course-cli") -> str:
    now = int(time.time())
    claims = {
        "iss": ISSUER,
        "sub": sub,
        "aud": audience,
        "client_id": client_id,
        "scope": scope,
        "iat": now,
        "exp": now + ttl,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(claims, private_key(), algorithm="RS256", headers={"kid": "dev-1"})


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["mint"])
    p.add_argument("--sub", default="alice")
    p.add_argument("--scope", default="notes:read")
    p.add_argument("--aud", default=RESOURCE)
    p.add_argument("--ttl", type=int, default=600)
    a = p.parse_args()
    print(mint(a.sub, a.scope, a.aud, a.ttl))
