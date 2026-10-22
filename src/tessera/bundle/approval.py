"""Verifiable approvals — the sign-off as a cryptographic artifact (spec 0145).

An approval is a **detached** JSON artifact: an Ed25519 signature over the
canonical bytes of a payload containing the bundle's sealed
``integrity.root`` (ADR 0035). It proves *who* (a key) approved *what* (the
exact sealed bytes): change one digit of the decision and re-seal, and the
root moves — every prior approval reads INVALID with the mismatch named.

Creating an approval needs the ``sign`` extra (the spec-0135 pattern);
**checking one is pure stdlib** via the RFC 8032 verifier, so
``tessera verify --approval a.json`` adds no dependency.

Honesty notes, load-bearing:

- An approval binds a **key**, not a human identity — key distribution and
  role mapping are out of scope (ADR 0032), here as for bundle signing.
- The optional ``at`` field is the approver's signed **claim**, not proof;
  proving *when* honestly needs a transparency log (the reserved anchor
  unit). No timestamp theater.
- Approvals **inform**; policies **enforce** (the ``approvals`` rule group
  in :mod:`tessera.bundle.policy` counts only valid ones, fail-closed).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tessera.bundle.canonical import canonical_bytes
from tessera.bundle.ed25519 import verify as ed25519_verify

APPROVAL_FORMAT = "tessera-approval"
APPROVAL_MAJOR = 1
_ALGORITHM = "ed25519"


@dataclass(frozen=True)
class ApprovalCheck:
    """One approval artifact's verification: the root it approves, the
    approver's public key, whether it is valid against *this* bundle, and —
    when it is not — the named problem."""

    approves_root: str
    approver: str
    valid: bool
    problem: str | None
    note: str | None
    at: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "approves_root": self.approves_root,
            "approver": self.approver,
            "valid": self.valid,
            "problem": self.problem,
            "note": self.note,
            "at": self.at,
        }


def _payload(root: str, note: str | None, at: str | None) -> dict[str, object]:
    """The exact signed payload — its canonical bytes are what the approver
    signs and what the checker verifies."""
    return {
        "format": {"name": APPROVAL_FORMAT, "major": APPROVAL_MAJOR},
        "approves_root": root,
        "note": note,
        "at": at,
    }


class ApprovalFormatError(ValueError):
    """The file is not a readable approval artifact (missing/malformed
    fields) — the caller's file-level failure, distinct from an approval
    that is readable but invalid against a bundle."""


def build_approval(
    bundle: dict[str, object],
    key_path: Path,
    *,
    note: str | None = None,
    at: str | None = None,
) -> dict[str, object]:
    """Sign an approval of ``bundle``'s sealed root with the Ed25519 key at
    ``key_path``. Needs the ``sign`` extra (clean error otherwise); checking
    never does."""
    from tessera.bundle.signing import _signing_key_class

    integrity = bundle.get("integrity")
    root = integrity.get("root") if isinstance(integrity, dict) else None
    if not isinstance(root, str) or not root:
        raise ValueError("cannot approve an unsealed bundle (no integrity.root)")

    signing_key_cls = _signing_key_class()
    if not key_path.exists():
        raise FileNotFoundError(
            f"no signing key at {key_path} — run `tessera bundle keygen` first"
        )
    seed = bytes.fromhex(key_path.read_text(encoding="utf-8").strip())
    key = signing_key_cls(seed)
    payload = _payload(root, note, at)
    signed = key.sign(canonical_bytes(payload))
    return {
        **payload,
        "approver": {
            "algorithm": _ALGORITHM,
            "public_key": bytes(key.verify_key).hex(),
        },
        "signature": signed.signature.hex(),
    }


def _read_artifact(
    artifact: dict[str, object],
) -> tuple[str, str, bytes, str | None, str | None, bytes]:
    """Strict shape extraction; raises :class:`ApprovalFormatError` naming
    the offending field."""
    fmt = artifact.get("format")
    if not isinstance(fmt, dict) or fmt.get("name") != APPROVAL_FORMAT:
        raise ApprovalFormatError(
            f"not an approval artifact: format.name is "
            f"{fmt.get('name') if isinstance(fmt, dict) else None!r}"
        )
    if fmt.get("major") != APPROVAL_MAJOR:
        raise ApprovalFormatError(
            f"unsupported approval major {fmt.get('major')!r} "
            f"(this verifier reads major {APPROVAL_MAJOR})"
        )
    root = artifact.get("approves_root")
    if not isinstance(root, str) or not root:
        raise ApprovalFormatError("approves_root is missing or not a string")
    approver = artifact.get("approver")
    if not isinstance(approver, dict) or approver.get("algorithm") != _ALGORITHM:
        raise ApprovalFormatError(
            "approver.algorithm must be 'ed25519' (missing or unsupported)"
        )
    public_hex = approver.get("public_key")
    signature_hex = artifact.get("signature")
    if not isinstance(public_hex, str) or not isinstance(signature_hex, str):
        raise ApprovalFormatError("approver.public_key / signature must be hex strings")
    try:
        public_key = bytes.fromhex(public_hex)
        signature = bytes.fromhex(signature_hex)
    except ValueError as error:
        raise ApprovalFormatError(f"not valid hex: {error}") from error
    if len(public_key) != 32 or len(signature) != 64:
        raise ApprovalFormatError(
            f"wrong key/signature length (public_key {len(public_key)}B, "
            "signature {len(signature)}B; expected 32B / 64B)"
        )
    note = artifact.get("note")
    at = artifact.get("at")
    if note is not None and not isinstance(note, str):
        raise ApprovalFormatError("note must be a string or null")
    if at is not None and not isinstance(at, str):
        raise ApprovalFormatError("at must be a string or null")
    return root, public_hex, public_key, note, at, signature


def check_approval(artifact: dict[str, object], bundle_root: str) -> ApprovalCheck:
    """Check one approval artifact against the bundle root the verifier
    *recomputed* (never a stored claim). Pure stdlib. A malformed artifact
    raises :class:`ApprovalFormatError`; a readable one always returns a
    named verdict."""
    root, public_hex, public_key, note, at, signature = _read_artifact(artifact)

    if root != bundle_root:
        return ApprovalCheck(
            approves_root=root,
            approver=public_hex,
            valid=False,
            problem=(
                "approves a different bundle: the artifact approves root "
                f"{root[:19]}…, this bundle's recomputed root is "
                f"{bundle_root[:19]}… — an approval binds to exact bytes"
            ),
            note=note,
            at=at,
        )

    payload = canonical_bytes(_payload(root, note, at))
    if not ed25519_verify(public_key, payload, signature):
        return ApprovalCheck(
            approves_root=root,
            approver=public_hex,
            valid=False,
            problem=(
                "the approval signature does not verify — the artifact was "
                "altered, or it was not produced by this key"
            ),
            note=note,
            at=at,
        )

    return ApprovalCheck(
        approves_root=root,
        approver=public_hex,
        valid=True,
        problem=None,
        note=note,
        at=at,
    )
