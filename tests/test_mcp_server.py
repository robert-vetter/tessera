"""Tests for the MCP server (Milestone 11 Unit 4, spec 0084).

Two layers, matching the design: the MCP-free tool handlers are unit-tested in CI
(no SDK needed); the SDK wiring is contract-tested only where the opt-in ``agent``
extra is installed (skipped in CI, which stays pure-stdlib). A subprocess pin proves
importing the server module never pulls ``mcp`` — the clone-and-run guarantee.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from typing import cast

import pytest

from tessera.agent.mcp_server import (
    tool_assertions,
    tool_draft_action,
    tool_ground,
    tool_list_actions,
    tool_list_domains,
)
from tessera.business.knowledge import build_demo_graph

# --- the MCP-free handlers (run in CI, no SDK) --------------------------------


def test_handler_ground_grounds_and_verifies() -> None:
    result = tool_ground(
        "devex", "Why did run R-1042 fail, and has this happened before?"
    )
    assert result["grounded"] is True
    assert result["refused"] is False
    assert result["all_verified"] is True
    assert result["claims"]
    # JSON-native (the server hands this straight to the MCP client).
    assert json.loads(json.dumps(result)) == result


def test_handler_ground_carries_refusal() -> None:
    result = tool_ground("business", "What is the capital of France?")
    assert result["refused"] is True
    assert result["grounded"] is False
    assert result["refusal"]
    assert result["claims"] == []


def test_handler_list_domains() -> None:
    payload = tool_list_domains()
    domains = cast("list[dict[str, str]]", payload["domains"])
    names = [d["name"] for d in domains]
    assert names == ["business", "devex", "github_actions"]
    assert all(d["description"] for d in domains)


def test_handler_assertions_returns_trail() -> None:
    node = build_demo_graph().resolutions[0].node_a
    payload = tool_assertions("business", node)
    assert payload["record_id"] == node
    assert payload["assertions"]
    assert json.loads(json.dumps(payload)) == payload


def test_handler_list_actions() -> None:
    payload = tool_list_actions()
    actions = cast("list[dict[str, object]]", payload["actions"])
    names = {a["name"] for a in actions}
    assert names == {"incident", "pr_summary"}
    assert all(a["description"] for a in actions)
    assert json.loads(json.dumps(payload)) == payload


def test_handler_draft_action_grounds_and_carries_refusal() -> None:
    drafted = tool_draft_action(
        "incident", "devex", "Why did run R-1042 fail, and has this happened before?"
    )
    assert drafted["grounded"] is True
    assert drafted["all_grounded"] is True
    assert drafted["requires_approval"] is True
    assert drafted["executed"] is False
    assert drafted["fields"]
    # JSON-native (handed straight to the MCP client).
    assert json.loads(json.dumps(drafted)) == drafted
    # A route-incompatible request crosses as a carried refusal, never a draft.
    refused = tool_draft_action("incident", "devex", "What does PR-201 change?")
    assert refused["refused"] is True
    assert refused["grounded"] is False
    assert refused["fields"] == []


# --- the opt-in-extra guarantee (run in CI) -----------------------------------


def test_importing_mcp_server_does_not_pull_the_sdk() -> None:
    """The clone-and-run guarantee: importing the server module (and so the whole
    default graph) must not import the optional ``mcp`` SDK — it is pulled only
    inside build_server()/main(). Mirrors the hdbcli default-import pin. Run in a
    subprocess so the test session's own imports don't pollute the check."""
    code = (
        "import sys, tessera.agent.mcp_server; "
        "assert 'mcp' not in sys.modules, 'mcp leaked into the default import graph'"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr


# --- the SDK wiring contract (skipped in CI; runs with `--extra agent`) --------


def test_build_server_registers_the_tools() -> None:
    """Contract: build_server() exposes the three read-only tools with descriptions
    and the expected input schemas, and dispatching `ground` through the server
    returns the handler's verified, serializable result. Requires the `agent`
    extra; skipped where the SDK is absent (CI is pure-stdlib by design)."""
    pytest.importorskip("mcp")
    from tessera.agent.mcp_server import build_server

    server = build_server()

    tools = {t.name: t for t in asyncio.run(server.list_tools())}
    assert set(tools) == {
        "list_domains",
        "ground",
        "assertions",
        "list_actions",
        "draft_action",
    }
    for tool in tools.values():
        assert tool.description
    assert set(tools["ground"].inputSchema["properties"]) == {"domain", "question"}
    assert set(tools["assertions"].inputSchema["properties"]) == {"domain", "record_id"}
    assert set(tools["draft_action"].inputSchema["properties"]) == {
        "action",
        "domain",
        "question",
    }

    result = asyncio.run(
        server.call_tool(
            "ground",
            {"domain": "github_actions", "question": "Why did the pages deploy fail?"},
        )
    )
    structured = result[1] if isinstance(result, tuple) else result
    assert isinstance(structured, dict)
    assert structured["grounded"] is True
    assert structured["all_verified"] is True
    assert structured["claims"]


def test_build_server_refusal_through_the_protocol() -> None:
    pytest.importorskip("mcp")
    from tessera.agent.mcp_server import build_server

    server = build_server()
    result = asyncio.run(
        server.call_tool(
            "ground", {"domain": "devex", "question": "What is the capital of France?"}
        )
    )
    structured = result[1] if isinstance(result, tuple) else result
    assert isinstance(structured, dict)
    assert structured["refused"] is True
    assert structured["claims"] == []
    assert structured["refusal"]


def test_build_server_drafts_an_action_through_the_protocol() -> None:
    """Contract: dispatching draft_action through the server returns the serialized,
    field-verified, propose-and-approve proposal. Requires the `agent` extra."""
    pytest.importorskip("mcp")
    from tessera.agent.mcp_server import build_server

    server = build_server()
    result = asyncio.run(
        server.call_tool(
            "draft_action",
            {
                "action": "incident",
                "domain": "devex",
                "question": "Why did run R-1042 fail, and has this happened before?",
            },
        )
    )
    structured = result[1] if isinstance(result, tuple) else result
    assert isinstance(structured, dict)
    assert structured["grounded"] is True
    assert structured["all_grounded"] is True
    assert structured["requires_approval"] is True
    assert structured["executed"] is False
    assert structured["fields"]
