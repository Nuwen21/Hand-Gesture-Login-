import hashlib
import os
import hmac

ITERATIONS = 150_000


def hash_secret(secret: str, salt: str | None = None) -> tuple[str, str]:
    """Return (salt_hex, hash_hex) for a password or gesture string."""
    if salt is None:
        salt_bytes = os.urandom(16)
        salt = salt_bytes.hex()
    else:
        salt_bytes = bytes.fromhex(salt)

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        secret.encode("utf-8"),
        salt_bytes,
        ITERATIONS,
    ).hex()
    return salt, digest


def verify_secret(secret: str, salt: str, expected_hash: str) -> bool:
    """Safely compare a new secret against a stored salted hash."""
    _, actual_hash = hash_secret(secret, salt)
    return hmac.compare_digest(actual_hash, expected_hash)
