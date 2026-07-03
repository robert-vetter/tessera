"""Root-cause analysis: why a pipeline run failed, grounded in its log.

The DevEx milestone behaviour (spec 0029): given *"why did run R-1042
fail?"*, surface the run's outcome row, the exact log lines that failed, and
— the valuable part — whether this same failure **happened before**: an
earlier run whose log carries the same error signature, and any ticket that
documents it. Every claim is evidence: run rows and log sections are quoted
verbatim (verifier shape 1), and cross-source assertions use the
shared-fragment grammar the verifier recomputes (`"<signature>" appears in
'<source A>' and '<source B>'` — every fragment checked against every cited
record).

Honesty boundaries: a *hypothesis* here is a recurrence/incident link, never
a causal invention; the first occurrence of a failure gets no recurrence
claim (there is nothing prior); a run that **passed** is a refused premise,
not a confabulated failure; an unknown run is refused by name. Deterministic
throughout — no LLM (ADR 0006 stands for this vertical too).
"""

from __future__ import annotations

import re

from tessera.graph import KnowledgeGraph, Node
from tessera.grounding import Answer, Claim
from tessera.resolution import normalize

# A run is named by the synthetic 'R-####' id OR a real GitHub Actions run id
# (8+ digits) — the same RCA path serves both the synthetic corpus and the real
# connector (spec 0046). A non-existent id of either shape is refused by name.
RUN_ID = re.compile(r"\bR-\d{3,5}\b|\b\d{8,}\b")
# 'ERROR payments-service: TimeoutError: …' — the colon after the token
# excludes the 'ERROR job <name> failed' trailer line on purpose (spec 0029).
_ERROR_LINE = re.compile(r"ERROR \S+: (.+)$", re.MULTILINE)
# Real GitHub Actions runner logs mark a failure '##[error]<message>' rather than
# the synthetic 'ERROR <svc>: …' shape (spec 0046). Recognized ADDITIVELY: the
# synthetic logs still match _ERROR_LINE first, so their numbers do not move.
_GH_ERROR_MARKER = "##[error]"
_GH_ERROR_LINE = re.compile(r"##\[error\](.+)$", re.MULTILINE)
# The information-free runner trailer ('##[error]Process completed with exit
# code 1.'): a valid failure marker but a weak recurrence signature — two
# unrelated failures share it. Preferred AGAINST when any sharper error line
# exists (spec 0126); when a log carries nothing else, it is still used, and
# `tessera smoke` still warns on the resulting weak recurrence claim.
# Negative codes are real on Windows runners (review finding: `-?`); this
# regex and smoke's `_TRAILER` encode the same definition and move together.
_GENERIC_TRAILER = re.compile(r"^Process completed with exit code -?\d+\.?$")

NO_RUN_REFUSAL = (
    "I can't find a pipeline run in that question — name one, "
    "e.g. 'Why did run R-1042 fail?'."
)


def _unknown_run_refusal(run_id: str) -> str:
    return f"There is no run {run_id} in the knowledge graph."


def _passed_refusal(run: Node) -> str:
    return (
        f"Run {run.record.id.removeprefix('Run:')} did not fail — it passed. "
        "There is no failure to explain."
    )


def _log_chunks(graph: KnowledgeGraph, run_id: str) -> list[Node]:
    chunk_ids = graph.sources_of({run_id}, "log_of")
    return sorted((graph.node(cid) for cid in chunk_ids), key=lambda n: n.id)


def _error_chunks(chunks: list[Node]) -> list[Node]:
    return [
        chunk
        for chunk in chunks
        if "ERROR" in chunk.record.text or _GH_ERROR_MARKER in chunk.record.text
    ]


def _error_lines(chunk: Node) -> list[str]:
    """Every parseable error line in one chunk: the synthetic 'ERROR <svc>: …'
    shape's lines first (the same per-chunk precedence the old single-line
    scan had), then the real '##[error]' shape's, each in document order.
    Whitespace-only remainders (a bare '##[error]   ' marker) are dropped —
    an empty signature would "appear" in every record (review finding)."""
    text = chunk.record.text
    lines = [match.group(1) for match in _ERROR_LINE.finditer(text)]
    lines.extend(match.group(1).strip() for match in _GH_ERROR_LINE.finditer(text))
    return [line for line in lines if line.strip()]


def _verifiable(line: str) -> bool:
    """Only fragments the shared-fragment grammar can actually check.

    The verifier parses '"FRAGMENT" appears in …' — a double quote inside the
    fragment breaks or truncates that parse — and requires the normalized
    fragment to be non-empty (a non-alphanumeric-only line normalizes to "").
    A candidate failing either would yield a claim our OWN verifier rejects;
    emitting one is forbidden (ADR 0005, spec 0029), so it is never selected
    (review finding — the sharper-preference must not outrun the grammar)."""
    return '"' not in line and bool(normalize(line))


def _signature(chunks: list[Node]) -> tuple[str, Node] | None:
    """The run's error signature and the chunk it was extracted from.

    Selection (spec 0126): the first VERIFIABLE, NON-GENERIC error line
    across the run's error chunks (e.g. 'Creating Pages deployment failed');
    else the first verifiable line of any kind — so a trailer-only log still
    yields the weak 'Process completed with exit code N.' signature, which
    `tessera smoke` flags; else None, and the RCA answer simply carries no
    recurrence/incident claims (verbatim error chunks still speak). Returning
    the extraction chunk makes it the shared-fragment anchor — the old
    `error_chunks[0]` broke on logs whose first error-marked chunk carries no
    parseable error line (the M18 mkdocs smoke FAIL), and an
    incidentally-matching earlier chunk must not displace the true source."""
    candidates = [(line, chunk) for chunk in chunks for line in _error_lines(chunk)]
    verifiable = [pair for pair in candidates if _verifiable(pair[0])]
    for line, chunk in verifiable:
        if not _GENERIC_TRAILER.match(line):
            return line, chunk
    return verifiable[0] if verifiable else None


def _shared_fragment_claim(fragment: str, supports: list[Node], label: str) -> Claim:
    """A claim in the verifier's shared-fragment grammar: the quoted fragment
    must appear in every cited record; the named sources are the citations'."""
    sources = sorted({node.record.origin.source for node in supports})
    named = " and ".join(f"'{source}'" for source in sources)
    return Claim(
        text=f'{label}: "{fragment}" appears in {named}.',
        support=tuple(node.record for node in supports),
    )


def explain_failure(question: str, graph: KnowledgeGraph) -> Answer:
    """Answer "why did run X fail?" with grounded claims, or refuse with why."""
    match = RUN_ID.search(question)
    if match is None:
        return Answer(question=question, claims=(), refusal=NO_RUN_REFUSAL)
    run_id = f"Run:{match.group(0)}"

    try:
        run = graph.node(run_id)
    except KeyError:
        return Answer(
            question=question,
            claims=(),
            refusal=_unknown_run_refusal(match.group(0)),
        )

    if run.attr("status") != "failed":
        return Answer(question=question, claims=(), refusal=_passed_refusal(run))

    # 1) The run's outcome row — quoted verbatim, cited to itself.
    claims: list[Claim] = [Claim(text=run.record.text, support=(run.record,))]

    # 2) The failing log lines — each error-bearing section, quoted verbatim.
    error_chunks = _error_chunks(_log_chunks(graph, run_id))
    claims.extend(
        Claim(text=chunk.record.text, support=(chunk.record,)) for chunk in error_chunks
    )

    found = _signature(error_chunks)
    if found is not None:
        signature, anchor = found

        # 3) Recurrence: the same signature in an EARLIER run's log.
        started = run.attr("started") or ""
        prior_chunks: list[Node] = []
        for node in graph.nodes:
            if node.kind != "document" or signature not in node.record.text:
                continue
            owner_runs = [
                edge.dst
                for edge in graph.edges
                if edge.src == node.id and edge.relation == "log_of"
            ]
            if not owner_runs or owner_runs[0] == run_id:
                continue
            owner = graph.node(owner_runs[0])
            if (owner.attr("started") or "") < started:
                prior_chunks.append(node)
        prior_chunks.sort(key=lambda n: n.id)
        if prior_chunks:
            claims.append(
                _shared_fragment_claim(
                    signature, [anchor, *prior_chunks], "Recurring failure"
                )
            )

        # 4) Documented incidents: tickets that quote the signature.
        tickets = sorted(
            (
                node
                for node in graph.nodes
                if node.kind == "Ticket" and signature in node.record.text
            ),
            key=lambda n: n.id,
        )
        for ticket in tickets:
            claims.append(
                _shared_fragment_claim(
                    signature, [anchor, ticket], "Documented incident"
                )
            )
            claims.append(Claim(text=ticket.record.text, support=(ticket.record,)))
            # 5) The fix: the PR that resolves THIS incident, and its diff — one
            #    more hop, turning RCA into a genuine mixed-modality chain
            #    (run row -> log -> prior log -> ticket -> PR row -> diff).
            claims.extend(_fix_chain_claims(graph, ticket))

    return Answer(question=question, claims=tuple(claims), refusal=None)


def _fix_chain_claims(graph: KnowledgeGraph, ticket: Node) -> list[Claim]:
    """The PR(s) that resolve an incident ticket, plus the diff that did it.

    The link is the *exact* ticket id via the reversed ``motivated_by`` edge
    (extracted at ingestion from the PR's own description): so the fix for
    DEVEX-187 is PR-198, never PR-201 (which fixes the follow-up DEVEX-204) —
    the mis-pivot trap is avoided structurally, not by heuristic. The link is a
    neutral shared-fragment claim (the ticket id appears in both records); the
    "Fixes" language lives in the PR row's own verbatim text. No fixing PR ->
    no claim (an open incident like DEVEX-231 stops here, honestly)."""
    claims: list[Claim] = []
    ticket_ref = ticket.record.id.removeprefix("Ticket:")
    for pr_id in sorted(graph.sources_of({ticket.record.id}, "motivated_by")):
        pr = graph.node(pr_id)
        claims.append(_shared_fragment_claim(ticket_ref, [ticket, pr], "Resolved by"))
        claims.append(Claim(text=pr.record.text, support=(pr.record,)))
        for hunk_id in sorted(graph.sources_of({pr_id}, "diff_of")):
            hunk = graph.node(hunk_id)
            claims.append(Claim(text=hunk.record.text, support=(hunk.record,)))
    return claims
