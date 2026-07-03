"""Scrub foreign text before it reaches disk: credentials out, terminals safe.

Foreign CI logs and PR bodies are attacker-shaped by definition (spec 0118
risk 1) and carry two distinct hazards, both neutralized here at the fetch
boundary (:mod:`tessera.connect.github` runs every byte it writes through
this module) with per-category counts recorded in the workspace manifest —
scrubbing is reported, never silent (spec 0117 decision 6):

1. **Credential shapes.** GitHub masks *registered* secrets as ``***`` in its
   own logs, but an echoed literal sails through, and a workspace may end up in
   a pilot's audit artifact. Named token/key patterns are replaced with a
   visible marker. The list is not exhaustive — it covers common,
   high-confidence shapes; genuinely novel secret formats can still pass, so
   this is defense-in-depth over public data, not a guarantee.
2. **Terminal control sequences.** Unstripped ANSI/OSC escapes and C0/C1
   control bytes in foreign text would reach a terminal verbatim through
   ``tessera ask`` / ``tessera connect`` output — a forged ``##[error]`` line
   (via ``\\r`` overwrite), an OSC-8 hyperlink pointing somewhere hostile, a
   window-title hijack. They are neutralized wherever foreign text is
   persisted, so every rendered claim is already clean.

Both are **single-line-preserving**: ``\\t`` (TSV column separator) and ``\\n``
(line separator) survive, everything else in the control ranges does not — so
scrubbing never moves a line number and the ``log-span`` locators cited by
claims stay true to the file as stored. (Job/step *names* are additionally
stripped of tabs at TSV-synthesis time; see :mod:`tessera.connect.github`.)
"""

from __future__ import annotations

import re

# The visible replacement — grep-able, obviously not original content.
SCRUB_MARKER = "***SCRUBBED***"

# Multi-byte terminal sequences, stripped whole (payload included) before the
# lone-control pass mops up any remainder. OSC first so its BEL/ST terminator
# goes with it; then CSI; the lone-escape and other Fe/Fs escapes are caught by
# _CONTROL below (which includes 0x1b).
_ANSI_OSC = re.compile(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")
_ANSI_CSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
# C0 (0x00-0x1f) and C1 (0x7f-0x9f) controls EXCEPT tab (0x09) and newline
# (0x0a). Includes 0x1b, so any lone/leftover escape is removed here too; C1 is
# stripped because a raw 0x9b is a CSI-equivalent a terminal will act on.
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")


def neutralize_controls(text: str) -> tuple[str, int]:
    """Remove terminal control sequences; return the text and how many fired.

    Preserves ``\\t`` and ``\\n`` (structural in the TSV), so line count and
    column structure are untouched.
    """
    count = 0
    for pattern in (_ANSI_OSC, _ANSI_CSI):
        text, hits = pattern.subn("", text)
        count += hits
    text, hits = _CONTROL.subn("", text)
    return text, count + hits


# Named credential patterns. Each is (name, regex, replacement); replacements
# may keep a leading group so the *shape* stays readable (e.g. "Authorization:
# Bearer ***SCRUBBED***"). Whitespace classes are deliberately ``[ \t]`` and
# NEVER ``\s`` — ``\s`` matches ``\n``, and these run over the fully synthesized
# multi-line TSV, so a ``\s+`` before a value could reach across a line boundary
# and eat the next line's job column (a silent locator corruption). Keeping them
# line-local upholds the single-line invariant this module documents.
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
        "gitlab-pat",
        re.compile(r"\bglpat-[A-Za-z0-9_-]{16,}\b"),
        SCRUB_MARKER,
    ),
    (
        "npm-token",
        re.compile(r"\bnpm_[A-Za-z0-9]{30,}\b"),
        SCRUB_MARKER,
    ),
    (
        "aws-access-key",
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        SCRUB_MARKER,
    ),
    (
        "google-api-key",
        re.compile(r"\bAIza[A-Za-z0-9_-]{35}\b"),
        SCRUB_MARKER,
    ),
    (
        "openai-key",
        re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
        SCRUB_MARKER,
    ),
    (
        "slack-token",
        re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
        SCRUB_MARKER,
    ),
    (
        "jwt",
        re.compile(
            r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"
        ),
        SCRUB_MARKER,
    ),
    (
        "authorization-header",
        re.compile(
            r"(?i)\b(authorization[ \t]*:[ \t]*(?:bearer|token|basic)[ \t]+)\S+"
        ),
        rf"\g<1>{SCRUB_MARKER}",
    ),
    (
        # No leading ``\b``: a key like ``_authToken=`` sits inside a word
        # boundary, so requiring one would miss the common npm/CI case. Matching
        # from the keyword over-scrubs at worst (safe on credentials); the 8+
        # char value guard keeps it off innocent short assignments.
        "sensitive-assignment",
        re.compile(
            r"(?i)("
            r"(?:api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret"
            r"|token|secret|password|accountkey)"
            r"[ \t]*[=:][ \t]*)[A-Za-z0-9_./+-]{8,}"
        ),
        rf"\g<1>{SCRUB_MARKER}",
    ),
)


def scrub_text(text: str) -> tuple[str, dict[str, int]]:
    """Neutralize control sequences, then replace credential-shaped spans.

    Returns the cleaned text and per-category counts (only categories that
    actually fired appear), so an all-clean scrub is the empty dict — easy to
    assert on and honest in the manifest.
    """
    counts: dict[str, int] = {}
    text, control_hits = neutralize_controls(text)
    if control_hits:
        counts["control-sequences"] = control_hits
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


def scrub_line(text: str) -> str:
    """Scrub a single free-text line for safe display/persistence in the
    manifest and CLI output (miss strings interpolate foreign job/step names).
    Discards the counts — those are tallied on the primary written families."""
    scrubbed, _ = scrub_text(text)
    return scrubbed


def merge_counts(into: dict[str, int], sub: dict[str, int]) -> None:
    """Accumulate one scrub's counts into a running total (manifest bookkeeping)."""
    for name, hits in sub.items():
        into[name] = into.get(name, 0) + hits
