import base64
import hashlib
import os
import secrets

ALGO = "pbkdf2_sha256"
ITERATIONS = 200_000
SALT_BYTES = 16
KEY_LEN = 32


def hash_password(password: str) -> str:
    salt = os.urandom(SALT_BYTES)
    dk = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, ITERATIONS, dklen=KEY_LEN
    )
    return f"{ALGO}${ITERATIONS}${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters_str, b64_salt, b64_hash = stored.split("$")
        if algo != ALGO:
            return False
        iterations = int(iters_str)
        salt = base64.b64decode(b64_salt.encode())
        expected = base64.b64decode(b64_hash.encode())
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, iterations, dklen=len(expected)
        )
        return secrets.compare_digest(dk, expected)
    except Exception:
        return False
