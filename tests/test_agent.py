"""Tests for the grounded-tool layer (Milestone 11 Unit 3, spec 0083).

These pin the boundary contract an MCP server (Unit 4) will transport: every domain
grounds a real question and verifies its claims; an out-of-scope question is carried
as an explicit refusal, never an answer; provenance is serialized inline and round-
trips through JSON; and importing/calling the layer pulls no embedding / LLM / cloud
/ MCP module (the leak-guard, extended).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

from tessera.agent.grounded import (
    GroundedResult,
    assertions,
    available_domains,
    domain,
    ground,
)
from tessera.business.knowledge import build_demo_graph

# A representative question per domain that the deterministic router grounds.
_GROUNDED = {
    "business": "Compare Müller Logistik and Nordwind Logistik totals.",
    "devex": "Why did run R-1042 fail, and has this happened before?",
    "github_actions": "Why did the pages deploy fail?",
}


def test_available_domains() -> None:
    assert available_domains() == ("business", "devex", "github_actions")


def test_unknown_domain_raises() -> None:
    with pytest.raises(ValueError, match="unknown domain"):
        ground("finance", "anything")


@pytest.mark.parametrize("name", ["business", "devex", "github_actions"])
def test_each_domain_grounds_and_verifies(name: str) -> None:
    """A real question grounds, routes explainably, and every claim passes the
    boundary verifier — faithfulness preserved across the layer."""
    result = ground(name, _GROUNDED[name])
    assert isinstance(result, GroundedResult)
    assert result.grounded and not result.refused
    assert result.refusal is None
    assert result.claims
    assert result.route_kind and result.route_reason
    # Every claim is live-verified, and each carries inline provenance.
    assert result.all_verified
    for claim in result.claims:
        assert claim.verified
        assert claim.support
        for evidence in claim.support:
            assert evidence.id and evidence.source and evidence.text
            assert evidence.locator_kind


def test_refusal_is_carried_explicitly_not_answered() -> None:
    """An out-of-scope question stays a refusal across the boundary — it never
    becomes a fabricated answer (ADR 0022)."""
    result = ground("business", "What is the capital of France?")
    assert result.refused and not result.grounded
    assert result.refusal  # the reason is carried
    assert result.claims == ()
    assert result.all_verified  # vacuously true: no claim is unsupported


def test_to_dict_round_trips_through_json() -> None:
    """The result serializes to JSON-native types without losing a verdict, a
    refusal, or any provenance — the MCP server just json.dumps it."""
    result = ground("business", _GROUNDED["business"])
    payload = result.to_dict()
    restored = json.loads(json.dumps(payload))
    assert restored == payload
    assert restored["route"]["kind"] == result.route_kind
    assert restored["grounded"] is True
    assert restored["all_verified"] is True
    claim0 = restored["claims"][0]
    assert "verified" in claim0 and "support" in claim0
    ev0 = claim0["support"][0]
    assert {"id", "source", "locator", "ingested_at", "text"} <= set(ev0)
    assert {"kind", "parts", "render"} <= set(ev0["locator"])


def test_refusal_to_dict_carries_reason() -> None:
    payload = ground("devex", "What is the capital of France?").to_dict()
    assert payload["refused"] is True
    assert payload["grounded"] is False
    assert payload["refusal"]
    assert payload["claims"] == []


def test_assertions_surface_the_resolution_trail() -> None:
    """The ER provenance is inspectable: a resolved node's additive assertions
    come back with their reason and confidence, serializable."""
    graph = build_demo_graph()
    assert graph.resolutions, "expected the business graph to carry resolutions"
    node = graph.resolutions[0].node_a
    trail = assertions("business", node)
    assert trail, f"expected assertions touching {node}"
    kinds = {a.kind for a in trail}
    assert kinds <= {"resolution", "mention"}
    for item in trail:
        assert item.reason
        payload = item.to_dict()
        assert json.loads(json.dumps(payload)) == payload


def test_domain_metadata_is_descriptive() -> None:
    for name in available_domains():
        dom = domain(name)
        assert dom.name == name
        assert len(dom.description) > 40  # a usable tool description for an agent


def test_ground_output_is_deterministic_across_hash_seeds() -> None:
    """The serialized boundary result must be byte-stable regardless of
    PYTHONHASHSEED — a claim's co-supporting records are a set, so their order is
    sorted at the boundary (spec 0084). Run in subprocesses to vary the seed."""
    code = (
        "import json, sys; from tessera.agent.grounded import ground;"
        "print(json.dumps(ground('business',"
        "'What is Müller Logistik\\'s total order value?').to_dict(), sort_keys=True))"
    )

    def run(seed: str) -> str:
        env = {**os.environ, "PYTHONHASHSEED": seed}
        result = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, env=env
        )
        assert result.returncode == 0, result.stderr
        return result.stdout

    assert run("0") == run("1") == run("2026")


def test_agent_layer_pulls_no_embedding_llm_or_mcp_module() -> None:
    """The leak-guard, extended (ADR 0022): importing AND calling the grounded-tool
    layer must not pull any embedding / vector / embedding-ER / cloud-driver / MCP
    module — the layer is deterministic, offline, and lexical.

    ``tessera.platform.providers`` is intentionally NOT banned: it is pulled
    transitively by ``tessera.platform.__init__`` when the offline ``none``
    embeddings flag is read via ``platform.config``, and it contributes only
    protocol definitions and env-factory functions — no model is built and no
    network touched. The modules below are the real "a model/vector/protocol is on
    the path" signals. Run in a subprocess so other tests' imports don't pollute it.
    """
    code = (
        "import sys; from tessera.agent.grounded import ground;"
        "from tessera.agent.actions import draft_action;"
        "from tessera.agent.payloads import preview_payload;"
        "from tessera.agent.execution import execute_action;"
        "ground('business','Compare Müller Logistik and Nordwind Logistik totals.');"
        "ground('devex','Why did run R-1042 fail, and has this happened before?');"
        "ground('github_actions','Why did the pages deploy fail?');"
        "ground('business','What is the capital of France?');"
        "draft_action('incident','devex','Why did run R-1042 fail?');"
        "draft_action('pr_summary','devex','What does PR-201 change?');"
        "draft_action('incident','devex','What does PR-201 change?');"
        "preview_payload('incident','devex','Why did run R-1042 fail?');"
        "preview_payload('pr_summary','devex','What does PR-201 change?');"
        "preview_payload('incident','devex','Why did run R-1001 fail?');"
        "execute_action('incident','devex','Why did run R-1042 fail?');"
        "execute_action('pr_summary','devex','What does PR-201 change?');"
        "execute_action('incident','devex','What does PR-201 change?');"
        "banned={"
        "'tessera.semantic',"
        "'tessera.platform.vectors',"
        "'tessera.er_semantic',"
        "'hdbcli',"
        "'mcp'"
        "};"
        "leaked=banned & set(sys.modules);"
        "assert not leaked, sorted(leaked)"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
