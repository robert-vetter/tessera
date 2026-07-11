"""Emit a trust bundle: ground a question, package the closure, seal it.

Spec 0133 / ADR 0031. ``build_bundle`` replicates ``ground()``'s four
public steps (``domain()``, ``build()``, ``route()``, ``serialize_answer()``)
on a **fresh** graph/kb instance, so the packaged snapshot is by
construction the exact object the packaged verdicts were computed against —
no reach into the module-private engine cache. Corpus construction is
deterministic (spec 0132 pins round-trips on freshly built instances), and
a consistency test pins ``build_bundle().result == ground()``.

A refusal is a first-class outcome: it is packaged with the same closure
and sealed the same way — carrying a refusal is exactly the behaviour a
bundle must be able to prove.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from tessera.agent.grounded import domain, serialize_answer
from tessera.bundle.canonical import canonical_bytes
from tessera.bundle.format import (
    CLOSURE_FULL_SNAPSHOT,
    FORMAT_MAJOR,
    FORMAT_MINOR,
    FORMAT_NAME,
    seal,
)
from tessera.bundle.serde import graph_to_dict, kb_to_dict
from tessera.eval.metrics import ClaimShape


def engine_version() -> str:
    """The installed tessera version — the honest engine pin (spec 0131 D6)."""
    try:
        return version("tessera")
    except PackageNotFoundError:  # pragma: no cover - exotic environments only
        return "0.0.0"


def shape_identifiers(shapes: tuple[ClaimShape, ...]) -> list[str]:
    """The dotted identifiers of a domain's declared claim shapes, in order.

    A *proxy* pin — a body can change under a stable name — so unit 0134
    reads identifier equality **plus** version equality as "same grammar",
    and downgrades on any mismatch rather than guessing.
    """
    return [f"{shape.__module__}.{shape.__qualname__}" for shape in shapes]


def build_bundle(domain_name: str, question: str) -> dict[str, object]:
    """Ground ``question`` in ``domain_name`` and return the sealed bundle dict.

    Raises :class:`ValueError` for an unknown domain (propagated from the
    domain registry).
    """
    dom = domain(domain_name)
    graph, kb = dom.build()
    route, answer = dom.route(question, graph, kb)
    result = serialize_answer(
        answer,
        graph,
        dom.claim_shapes,
        domain=domain_name,
        question=question,
        route=route,
    )
    unsealed: dict[str, object] = {
        "format": {"name": FORMAT_NAME, "major": FORMAT_MAJOR, "minor": FORMAT_MINOR},
        "engine": {
            "tessera_version": engine_version(),
            "domain": domain_name,
            "claim_shapes": shape_identifiers(dom.claim_shapes),
        },
        "result": result.to_dict(),
        "evidence_closure": {
            "kind": CLOSURE_FULL_SNAPSHOT,
            "graph": graph_to_dict(graph),
            "kb": kb_to_dict(kb),
        },
        "action": None,
        "signature": None,
        "anchor": None,
    }
    return seal(unsealed)


def build_action_bundle(
    action: str, domain_name: str, question: str
) -> dict[str, object]:
    """Ground ``question``, draft and (simulated) execute ``action``, and
    package the receipt in the bundle's ``action`` section (spec 0136).

    A strict consumer of the frozen action chain: it runs
    :func:`~tessera.agent.execution.execute_action` through the **simulated**
    actuator (sends nothing) and packages the resulting receipt. Raises
    :class:`ValueError` if the action is not fully grounded on this question —
    a withheld action carries no wire request to verify. No real send is ever
    bundled here.
    """
    from tessera.agent.execution import execute_action

    receipt = execute_action(action, domain_name, question)
    if not receipt.all_grounded:
        raise ValueError(
            f"the '{action}' action is not grounded on this question "
            f"({receipt.withheld_reason or 'no verifier-passing fields'}); "
            "there is no wire request to bundle"
        )
    bundle = build_bundle(domain_name, question)
    unsealed = {key: value for key, value in bundle.items() if key != "integrity"}
    unsealed["action"] = receipt.to_dict()
    return seal(unsealed)


def bundle_bytes(bundle: dict[str, object]) -> bytes:
    """The exact file bytes: the canonical serialization plus one newline —
    so two machines emitting the same bundle write byte-identical files."""
    return canonical_bytes(bundle) + b"\n"


def write_bundle(bundle: dict[str, object], path: Path) -> int:
    """Write the sealed bundle to ``path``; returns the byte count written."""
    data = bundle_bytes(bundle)
    path.write_bytes(data)
    return len(data)
