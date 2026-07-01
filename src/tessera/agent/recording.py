"""Redact a real :class:`~tessera.agent.execution.ExecutionReceipt` for committing.

Milestone 15 Unit 3 (spec 0105). The real execution one-shot records an
``ExecutionReceipt`` from an actual GitHub send (spec 0106). The receipt never carries
the credential *by construction* — the ``Authorization`` header is built locally inside
``GithubActuator.execute`` and is never passed into the receipt — but a real ``created``
receipt's ``result["response"]`` is GitHub's echoed issue/comment JSON, which carries
volatile and identifying fields (the author ``user`` block, ``node_id``s, internal API
URLs, timestamps) that have no place in a committed provenance artifact.

:func:`redact_receipt` reduces that echoed response to a small, honest allow-list
(``number``/``html_url``/``state``/``title`` — enough to verify the send happened and
find the resource) and, as defense in depth, replaces the *value* of any token-like key
anywhere in the receipt with ``"***"``. It is a pure function over the receipt's
``to_dict()`` shape, so it is unit-tested offline and never touches the network.
gitleaks (pinned, enforced in pre-commit and CI) is the final secret-scan gate on the
committed artifact.
"""

from __future__ import annotations

import re

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
