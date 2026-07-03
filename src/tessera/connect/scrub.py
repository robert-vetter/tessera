"""Scrub credential-shaped content out of foreign text — before it reaches disk.

Foreign CI logs and PR bodies are attacker-shaped by definition (spec 0118
risk 1) and occasionally carry *accidents*: a token echoed by a misconfigured
step, an ``Authorization`` header in a dumped request. GitHub masks registered
secrets as ``***`` in its own logs, but only the ones a workflow registered —
an echoed literal sails through. Since a workspace snapshot may end up in a
pilot's audit artifact, anything credential-shaped is replaced with a visible
marker **at the fetch boundary** (:mod:`tessera.connect.github` scrubs every
byte it writes), and the per-pattern counts land in the workspace manifest —
scrubbing is reported, never silent (spec 0117 decision 6).

Every pattern is single-line, so scrubbing never moves a line number — the
``log-span`` locators cited by claims stay true to the file as stored.
"""

from __future__ import annotations

import re

# The visible replacement — grep-able, obviously not original content.
SCRUB_MARKER = "***SCRUBBED***"

# Named, auditable patterns. Each is (name, regex, replacement); replacements
# may keep a leading group so the *shape* of the line stays readable (e.g.
# "Authorization: Bearer ***SCRUBBED***"). The vocabulary of the key-value
# pattern mirrors the M15 receipt scrubber's sensitive-key regex
# (tessera.agent.recording), extended content-side for raw text.
_PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "github-token",
        re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{16,}\b"),
        SCRUB_MARKER,
    ),
    (
        "github-fine-grained-pat",
        re.compile(r"\bgithub_pat_[A-Za-z0-9_]{16,}\b"),
        SCRUB_MARKER,
    ),
    (
        "aws-access-key",
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        SCRUB_MARKER,
    ),
    (
        "slack-token",
        re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
        SCRUB_MARKER,
    ),
    (
        "authorization-header",
        re.compile(r"(?i)\b(authorization\s*:\s*(?:bearer|token|basic)\s+)\S+"),
        rf"\g<1>{SCRUB_MARKER}",
    ),
    (
        "sensitive-assignment",
        re.compile(
            r"(?i)\b((?:api[_-]?key|token|secret|password)\s*[=:]\s*)"
            r"[A-Za-z0-9_./+-]{8,}"
        ),
        rf"\g<1>{SCRUB_MARKER}",
    ),
)


def scrub_text(text: str) -> tuple[str, dict[str, int]]:
    """Replace credential-shaped spans; return the text and per-pattern counts.

    Counts contain only patterns that actually fired, so an all-clean scrub is
    the empty dict — easy to assert on and honest in the manifest.
    """
    counts: dict[str, int] = {}
    for name, pattern, replacement in _PATTERNS:
        text, hits = pattern.subn(replacement, text)
        if hits:
            counts[name] = counts.get(name, 0) + hits
    return text, counts


def scrub_json_values(value: object) -> tuple[object, dict[str, int]]:
    """Scrub every string value in a parsed-JSON structure, tallying counts.

    Keys are fixed API vocabulary and stay; values (names, titles, bodies,
    messages) are foreign content and get the same treatment as raw text.
    Rebuilds fresh containers — the input is never mutated.
    """
    counts: dict[str, int] = {}

    def merge(sub: dict[str, int]) -> None:
        for name, hits in sub.items():
            counts[name] = counts.get(name, 0) + hits

    def walk(node: object) -> object:
        if isinstance(node, str):
            scrubbed, sub = scrub_text(node)
            merge(sub)
            return scrubbed
        if isinstance(node, dict):
            return {key: walk(item) for key, item in node.items()}
        if isinstance(node, list):
            return [walk(item) for item in node]
        return node

    return walk(value), counts


def merge_counts(into: dict[str, int], sub: dict[str, int]) -> None:
    """Accumulate one scrub's counts into a running total (manifest bookkeeping)."""
    for name, hits in sub.items():
        into[name] = into.get(name, 0) + hits
