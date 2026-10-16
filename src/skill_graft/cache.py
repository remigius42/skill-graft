"""The cache of git sources: one bare repository per URL, one export per commit."""

import hashlib
import re

# Characters a cache folder name keeps; others become `_`.
UNSAFE = re.compile(r"[^A-Za-z0-9._-]")


def key(url: str) -> str:
    """`<last URL segment>-<hash>`: readable, and distinct per URL."""
    segment = re.split(r"[/:]", url.rstrip("/"))[-1].removesuffix(".git")
    name = UNSAFE.sub("_", segment) or "repo"
    return f"{name}-{hashlib.sha256(url.encode()).hexdigest()[:12]}"
