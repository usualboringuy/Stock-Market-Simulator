# src/api/security.py
import hashlib


def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()
