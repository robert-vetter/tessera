"""The Merkle tree behind the issuance ledger (spec 0151, ADR 0041).

An append-only log of issued receipt roots, built exactly as Certificate
Transparency builds one (RFC 6962), because the question it answers is the
same one: *is this all of them?* Two proofs make the log worth keeping:

- **inclusion** — this leaf is in the tree with that head;
- **consistency** — this head extends that earlier head **without
  rewriting anything**, so a decision cannot be quietly removed or altered
  once anyone has seen an earlier head.

Hashing is domain-separated (``0x00`` for leaves, ``0x01`` for interior
nodes) so a leaf can never be presented as an interior node — the classic
second-preimage attack on naive Merkle trees.

Pure stdlib, deterministic, offline. What this does **not** prove is
stated wherever the feature is documented: an operator keeping two logs
can show two heads, and no offline check detects that (see
``docs/LEDGER.md``).
"""

from __future__ import annotations

import hashlib

LEAF_PREFIX = b"\x00"
NODE_PREFIX = b"\x01"


def leaf_hash(value: str) -> bytes:
    """The hash of a log entry — domain-separated from interior nodes."""
    return hashlib.sha256(LEAF_PREFIX + value.encode("utf-8")).digest()


def node_hash(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(NODE_PREFIX + left + right).digest()


def _split(size: int) -> int:
    """The largest power of two strictly smaller than ``size`` — RFC 6962's
    split point, which is what makes the proofs' shapes canonical."""
    k = 1
    while k * 2 < size:
        k *= 2
    return k


def root(leaves: list[bytes]) -> bytes:
    """The Merkle tree head over ``leaves``. An empty log hashes to the
    empty-string digest, as RFC 6962 specifies."""
    if not leaves:
        return hashlib.sha256(b"").digest()
    if len(leaves) == 1:
        return leaves[0]
    k = _split(len(leaves))
    return node_hash(root(leaves[:k]), root(leaves[k:]))


def inclusion_proof(leaves: list[bytes], index: int) -> list[bytes]:
    """The audit path proving ``leaves[index]`` is in the tree."""
    if not 0 <= index < len(leaves):
        raise IndexError(f"no entry {index} in a log of size {len(leaves)}")
    if len(leaves) == 1:
        return []
    k = _split(len(leaves))
    if index < k:
        return inclusion_proof(leaves[:k], index) + [root(leaves[k:])]
    return inclusion_proof(leaves[k:], index - k) + [root(leaves[:k])]


def verify_inclusion(
    leaf: bytes, index: int, size: int, path: list[bytes], head: bytes
) -> bool:
    """Recompute the head from a leaf and its audit path.

    Pure arithmetic on hashes: the verifier needs the leaf, its position,
    the tree size and the path — never the log itself.
    """
    if not 0 <= index < size:
        return False
    computed = leaf
    node, last = index, size - 1
    for sibling in path:
        if node % 2 == 1 or node == last:
            computed = node_hash(sibling, computed)
            while node % 2 == 0 and node != 0:
                node //= 2
                last //= 2
        else:
            computed = node_hash(computed, sibling)
        node //= 2
        last //= 2
    return node == 0 and computed == head


def consistency_proof(leaves: list[bytes], old_size: int) -> list[bytes]:
    """The proof that the current tree extends the tree of ``old_size``."""
    size = len(leaves)
    if not 0 < old_size <= size:
        raise ValueError(f"cannot prove consistency from {old_size} to {size}")
    if old_size == size:
        return []
    return _consistency(leaves, old_size, True)


def _consistency(leaves: list[bytes], old_size: int, is_full: bool) -> list[bytes]:
    size = len(leaves)
    if old_size == size:
        # The old tree is a complete subtree: it needs to be named only when
        # it is not the caller's own root (RFC 6962's `b` flag).
        return [] if is_full else [root(leaves)]
    k = _split(size)
    if old_size <= k:
        return _consistency(leaves[:k], old_size, is_full) + [root(leaves[k:])]
    return _consistency(leaves[k:], old_size - k, False) + [root(leaves[:k])]


def verify_consistency(
    old_size: int, old_head: bytes, new_size: int, new_head: bytes, path: list[bytes]
) -> bool:
    """Check that ``new_head`` extends ``old_head`` with nothing rewritten.

    This is the check that turns an append-only *claim* into an append-only
    *property*: an operator who edits or drops an earlier entry cannot
    produce a path that reconstructs both heads.
    """
    if not 0 < old_size <= new_size:
        return False
    if old_size == new_size:
        return not path and old_head == new_head

    # Climb from the old tree's last leaf to the root of the largest complete
    # subtree it fills; that node is where the two trees still agree.
    node, last = old_size - 1, new_size - 1
    while node % 2 == 1:
        node //= 2
        last //= 2

    remaining = iter(path)
    try:
        # When the old tree was not a complete subtree, the proof must name
        # the node the two trees share; otherwise its head is the seed.
        seed = next(remaining) if node > 0 else old_head
        old_computed = seed
        new_computed = seed

        # Phase 1: rebuild both heads while the old tree still has siblings.
        while node > 0:
            if node % 2 == 1:
                sibling = next(remaining)
                old_computed = node_hash(sibling, old_computed)
                new_computed = node_hash(sibling, new_computed)
            elif node < last:
                new_computed = node_hash(new_computed, next(remaining))
            node //= 2
            last //= 2

        # Phase 2: the new tree keeps growing to the right on its own.
        while last > 0:
            new_computed = node_hash(new_computed, next(remaining))
            last //= 2
    except StopIteration:
        return False  # a truncated proof proves nothing

    if next(remaining, None) is not None:
        return False  # trailing material is not a valid proof either
    return old_computed == old_head and new_computed == new_head
