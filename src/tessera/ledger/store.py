"""The append-only issuance log and its detached proof artifact (spec 0151).

The log is a text file, one sealed bundle root per line, in issuance
order — deliberately the least clever storage that can exist, because the
guarantee comes from the Merkle proofs rather than from the container. A
reviewer can read the whole log with ``cat``.

Attestation never touches the bundle: like an approval (ADR 0035), the
inclusion proof is a **detached** artifact, so no root moves and no
signature or approval is invalidated.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from tessera.ledger.tree import (
    consistency_proof,
    inclusion_proof,
    leaf_hash,
    root,
    verify_consistency,
    verify_inclusion,
)

PROOF_FORMAT = "tessera-inclusion-proof"
PROOF_MAJOR = 1


class LedgerError(ValueError):
    """A named refusal (never a silently unusable log or proof)."""


@dataclass(frozen=True)
class Head:
    """What a verifying party must obtain out of band: the log's size and
    its Merkle head at the moment they saw it."""

    size: int
    root: str

    def __str__(self) -> str:
        return f"{self.size}:{self.root}"

    @classmethod
    def parse(cls, text: str) -> Head:
        size, _, digest = text.partition(":")
        if not size.isdigit() or not digest:
            raise LedgerError(f"malformed head {text!r} — expected '<size>:<sha256:…>'")
        return cls(size=int(size), root=digest)


class Ledger:
    """An append-only log of issued receipt roots."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def entries(self) -> list[str]:
        if not self.path.is_file():
            return []
        return [
            line.strip()
            for line in self.path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def _leaves(self) -> list[bytes]:
        return [leaf_hash(entry) for entry in self.entries()]

    def head(self) -> Head:
        leaves = self._leaves()
        return Head(size=len(leaves), root="sha256:" + root(leaves).hex())

    def append(self, bundle_root: str) -> int:
        """Record a receipt's root. Returns its index. Appending the same
        root twice is refused: a log with duplicates cannot answer 'which
        decision was this' unambiguously."""
        entries = self.entries()
        if bundle_root in entries:
            raise LedgerError(
                f"{bundle_root} is already entry {entries.index(bundle_root)} "
                "in this log"
            )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(bundle_root + "\n")
        return len(entries)

    def index_of(self, bundle_root: str) -> int:
        entries = self.entries()
        if bundle_root not in entries:
            raise LedgerError(
                f"{bundle_root} is not in this log — no inclusion proof exists "
                "for a receipt that was never recorded"
            )
        return entries.index(bundle_root)

    def prove(self, bundle_root: str) -> dict[str, object]:
        """The detached inclusion-proof artifact for a recorded receipt."""
        index = self.index_of(bundle_root)
        leaves = self._leaves()
        path = inclusion_proof(leaves, index)
        return {
            "format": {"name": PROOF_FORMAT, "major": PROOF_MAJOR},
            "proves_root": bundle_root,
            "index": index,
            "size": len(leaves),
            "head": "sha256:" + root(leaves).hex(),
            "path": ["sha256:" + node.hex() for node in path],
        }

    def consistency(self, old_size: int) -> dict[str, object]:
        """Proof that the current head extends an earlier one."""
        leaves = self._leaves()
        if not 0 < old_size <= len(leaves):
            raise LedgerError(
                f"cannot prove consistency from size {old_size}: this log has "
                f"{len(leaves)} entr{'y' if len(leaves) == 1 else 'ies'}"
            )
        return {
            "from": str(Head(old_size, "sha256:" + root(leaves[:old_size]).hex())),
            "to": str(self.head()),
            "path": [
                "sha256:" + node.hex() for node in consistency_proof(leaves, old_size)
            ],
        }


def _unhex(value: object, what: str) -> bytes:
    if not isinstance(value, str) or not value.startswith("sha256:"):
        raise LedgerError(f"{what} is not a sha256 digest")
    try:
        return bytes.fromhex(value.removeprefix("sha256:"))
    except ValueError as error:
        raise LedgerError(f"{what} is not valid hex: {error}") from error


def check_inclusion(
    artifact: dict[str, object], bundle_root: str, head: Head
) -> str | None:
    """Check a detached inclusion proof against a head the VERIFIER supplies.

    Returns ``None`` when the proof holds, otherwise a named problem. The
    head is never taken from the artifact: a proof that vouches for its own
    head is self-attestation, which is the failure mode this whole project
    exists to answer.
    """
    fmt = artifact.get("format")
    if not isinstance(fmt, dict) or fmt.get("name") != PROOF_FORMAT:
        return "not an inclusion-proof artifact"
    if fmt.get("major") != PROOF_MAJOR:
        return f"unsupported proof major {fmt.get('major')!r}"
    if artifact.get("proves_root") != bundle_root:
        return (
            f"the proof is for {artifact.get('proves_root')}, not for this "
            f"bundle's root {bundle_root}"
        )
    index, size = artifact.get("index"), artifact.get("size")
    if not isinstance(index, int) or not isinstance(size, int):
        return "the proof's index/size are malformed"
    if size != head.size:
        return (
            f"the proof is against a log of size {size}, but the head you "
            f"supplied is size {head.size}"
        )
    raw_path = artifact.get("path")
    if not isinstance(raw_path, list):
        return "the proof carries no audit path"
    try:
        path = [_unhex(node, "an audit-path node") for node in raw_path]
        expected = _unhex(head.root, "the supplied head")
    except LedgerError as error:
        return str(error)
    if not verify_inclusion(leaf_hash(bundle_root), index, size, path, expected):
        return (
            "the audit path does not reconstruct the head you supplied — this "
            "receipt is not in that log"
        )
    return None


def check_consistency(artifact: dict[str, object]) -> str | None:
    """Check a consistency proof between the two heads it names."""
    try:
        old = Head.parse(str(artifact.get("from", "")))
        new = Head.parse(str(artifact.get("to", "")))
    except LedgerError as error:
        return str(error)
    raw_path = artifact.get("path")
    if not isinstance(raw_path, list):
        return "the proof carries no path"
    try:
        path = [_unhex(node, "a path node") for node in raw_path]
        old_root = _unhex(old.root, "the earlier head")
        new_root = _unhex(new.root, "the later head")
    except LedgerError as error:
        return str(error)
    if not verify_consistency(old.size, old_root, new.size, new_root, path):
        return (
            "the later head does not extend the earlier one — history was "
            "rewritten, or the proof is wrong"
        )
    return None


def load_proof(path: Path) -> dict[str, object]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise LedgerError(f"cannot read proof {path}: {error}") from error
    if not isinstance(parsed, dict):
        raise LedgerError(f"{path} is not a JSON object")
    return parsed
