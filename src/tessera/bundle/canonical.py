"""Canonical bytes for trust bundles — ``tessera-canonical-json-1``.

Spec 0133 / ADR 0031. The recipe is the one that already produces the
cross-process-stable idempotency key (``agent/execution.py``'s
``_canonical_request``, ADR 0026), generalized here without touching that
module: ``json.dumps`` with sorted keys, non-ASCII preserved, minimal
separators, UTF-8-encoded.

**Deliberately not RFC 8785 (JCS)** and never claimed to be: the chain's
data model is strings + ``Decimal`` end-to-end (the only floats are ER
confidences, which Python's repr-based JSON round-trips exactly — pinned
by spec 0132's fidelity tests), so JCS's ECMAScript number serialization
would buy nothing and cost platform-sensitive float machinery. The recipe
identifier is recorded inside every bundle, so a change is a visible
format event, never a silent drift.
"""

from __future__ import annotations

import hashlib
import json

# The recipe identifier recorded in every bundle (integrity.canonicalization).
CANONICALIZATION = "tessera-canonical-json-1"


def canonical_bytes(value: object) -> bytes:
    """The canonical byte serialization of a JSON-representable value."""
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    """The ``sha256:<hex>`` digest string used for every leaf and root."""
    return "sha256:" + hashlib.sha256(data).hexdigest()


def digest(value: object) -> str:
    """Canonicalize and hash in one step — the leaf recipe."""
    return sha256_hex(canonical_bytes(value))
