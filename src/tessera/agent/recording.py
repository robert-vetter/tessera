"""Redaction + persistence policy for the real-execution one-shot record.

Milestone 15 Unit 3 (spec 0105); persistence policy Milestone 16 Unit 2 (spec 0109,
audit B1). The real execution one-shot records an ``ExecutionReceipt`` from an actual
GitHub send. The receipt never carries the credential *by construction* — the
``Authorization`` header is built locally inside ``GithubActuator.execute`` and is
never passed into the receipt — but a real ``created`` receipt's ``result["response"]``
is GitHub's echoed issue/comment JSON, which carries volatile and identifying fields
(the author ``user`` block, ``node_id``s, internal API URLs, timestamps) that have no
place in a committed provenance artifact.

:func:`redact_receipt` reduces that echoed response to a small, honest allow-list
(``number``/``html_url``/``state``/``title`` — enough to verify the send happened and
find the resource) and, as defense in depth, replaces the *value* of any token-like key
anywhere in the receipt with ``"***"``. It is a pure function over the receipt's
``to_dict()`` shape, so it is unit-tested offline and never touches the network.
gitleaks (pinned, enforced in pre-commit and CI) is the final secret-scan gate on the
committed artifact.

:func:`should_persist` and :func:`guard_no_clobber` are the recorder's persistence
policy (audit B1): only a **consummated** outcome (``created``/``exists``) is written,
and an existing receipt on disk is **never overwritten** — the one-shot's artifact is
historic. An approved attempt that ends in any other outcome (``withheld`` /
``inconclusive`` / ``error`` — and, defensively, ``blocked``) is printed for
inspection but not persisted, so a failed attempt can neither block a retry nor
clobber the record.
"""

from __future__ import annotations

import re
from pathlib import Path

# The only fields of GitHub's echoed response worth committing: enough to verify the
# send and locate the resource, nothing identifying or volatile. An allow-list (not a
# deny-list) so a field GitHub adds later is dropped by default, not leaked by omission.
_RESPONSE_KEEP = ("number", "html_url", "state", "title")

# Defense in depth: any key that looks like a secret has its value replaced, wherever it
# sits in the receipt. The credential is already absent by construction; this guards
# against a future field or a nested echo carrying one.
_SENSITIVE_KEY = re.compile(
    r"token|secret|authorization|password|api[_-]?key", re.IGNORECASE
)

_REDACTED = "***"


def _redact(value: object) -> object:
    """Recursively rebuild ``value`` into fresh containers, replacing the value of any
    key matching :data:`_SENSITIVE_KEY` with ``"***"``. Builds new dicts/lists, so the
    input is never mutated; scalars pass through unchanged."""
    if isinstance(value, dict):
        out: dict[str, object] = {}
        for key, item in value.items():
            out[key] = _REDACTED if _SENSITIVE_KEY.search(key) else _redact(item)
        return out
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


# The only outcomes worth persisting: the one-shot itself ("created"), or "exists" as
# the crash-recovery record — a send whose receipt was lost between POST and write is
# recovered by the re-run's pre-check finding the marker. (Once a receipt exists on
# disk, guard_no_clobber refuses before any network, so "exists" is never recorded as
# a live re-run demonstration.) Everything else is a non-event or a failure the
# maintainer fixes and retries — printing it suffices; persisting it would either
# block the retry or overwrite history (audit B1).
_PERSISTED_OUTCOMES = frozenset({"created", "exists"})


def should_persist(outcome: str) -> bool:
    """True iff an approved attempt with this ``outcome`` is written to
    ``data/execution/``. Only a consummated send (``created``) or a verified prior one
    (``exists``, the crash-recovery case) is a record; every other outcome
    (``withheld``/``inconclusive``/``error`` — and defensively ``blocked``) is
    printed, never persisted (audit B1). Honesty note (review M3): an ``exists``
    record is only as trustworthy as the matched item's authorship — the marker is a
    deterministic function of a public payload, so the maintainer verifies the
    printed ``html_url`` is their own issue before committing the receipt (ADR 0026
    addendum)."""
    return outcome in _PERSISTED_OUTCOMES


def guard_no_clobber(out_dir: Path) -> None:
    """Refuse (``SystemExit``) when ``out_dir`` already holds a recorded receipt — the
    one-shot's artifact is historic and is never overwritten (audit B1). Run this
    *before any network activity*, so a re-run against an already-recorded one-shot
    sends nothing and touches nothing. The match is case-insensitive (review F5: on a
    case-insensitive filesystem ``RECEIPT.json`` names the same file a later write
    would truncate)."""
    existing = sorted(
        p.name for p in out_dir.glob("receipt*.json", case_sensitive=False)
    )
    if existing:
        raise SystemExit(
            "refusing to run: a recorded receipt already exists in "
            f"{out_dir} ({', '.join(existing)}). The one-shot artifact is historic — "
            "it is never overwritten. If you truly intend a new record, move the "
            "existing receipt (and its MANIFEST.json) OUT of this directory first."
        )


def redact_receipt(receipt: dict[str, object]) -> dict[str, object]:
    """Return a copy of a receipt ``to_dict()`` safe to commit: any token-like value is
    replaced with ``"***"``, and GitHub's echoed ``result["response"]`` (if a dict) is
    reduced to the ``number``/``html_url``/``state``/``title`` allow-list. The input is
    not mutated. Non-response results (a withheld/blocked/exists/inconclusive reason, a
    simulated marker) pass through unchanged."""
    redacted = _redact(receipt)
    if not isinstance(redacted, dict):  # pragma: no cover - a receipt is always a dict
        raise TypeError("a receipt must serialize to a JSON object")
    result = redacted.get("result")
    if isinstance(result, dict):
        response = result.get("response")
        if isinstance(response, dict):
            result["response"] = {
                key: response[key] for key in _RESPONSE_KEEP if key in response
            }
    return redacted
