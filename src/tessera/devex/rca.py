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

RUN_ID = re.compile(r"\bR-\d{3,5}\b")
# 'ERROR payments-service: TimeoutError: …' — the colon after the token
# excludes the 'ERROR job <name> failed' trailer line on purpose (spec 0029).
_ERROR_LINE = re.compile(r"ERROR \S+: (.+)$", re.MULTILINE)

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
    return [chunk for chunk in chunks if "ERROR" in chunk.record.text]


def _signature(chunks: list[Node]) -> str | None:
    """The first error signature in the run's error chunks."""
    for chunk in chunks:
        match = _ERROR_LINE.search(chunk.record.text)
        if match:
            return match.group(1)
    return None


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

    signature = _signature(error_chunks)
    if signature is not None and error_chunks:
        anchor = error_chunks[0]

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

    return Answer(question=question, claims=tuple(claims), refusal=None)
