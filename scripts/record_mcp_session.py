"""Record a real MCP client <-> server session against ``tessera-mcp``.

The "ran on" honesty for Milestones 11 and 12 (specs 0084, 0090): this spawns the
Tessera MCP server as a subprocess and drives it with a *real* MCP client over stdio —
listing tools, grounding a question in each domain, taking a principled refusal,
inspecting an entity-resolution trail, and **drafting propose-and-approve actions** (an
incident, a PR summary, and a carried refusal) — then writes the exchange to
``data/mcp_session/`` as a committed artifact (the no-spend analogue of the
Milestone-5 GitHub-Actions snapshot).

It is NOT run in CI (CI is pure-stdlib and carries no MCP SDK). Reproduce locally:

    uv run --extra agent python scripts/record_mcp_session.py

The structured tool results are deterministic (the engine is), so re-running yields
the same transcript modulo the header note.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "mcp_session"

# The scripted exchange: (tool, arguments, why).
CALLS: list[tuple[str, dict[str, str], str]] = [
    (
        "ground",
        {
            "domain": "business",
            "question": "What is Müller Logistik's total order value?",
        },
        "a grounded business lookup — a sourced aggregate",
    ),
    (
        "ground",
        {
            "domain": "devex",
            "question": "Why did run R-1042 fail, and has this happened before?",
        },
        "a grounded DevEx root-cause with recurrence",
    ),
    (
        "ground",
        {"domain": "github_actions", "question": "Why did the pages deploy fail?"},
        "a grounded answer over the real GitHub Actions connector",
    ),
    (
        "ground",
        {"domain": "business", "question": "What is the capital of France?"},
        "a principled refusal — carried across the protocol, never an answer",
    ),
]

# The grounded-ACTION calls (Milestone 12, spec 0090): (arguments, why). Each drafts a
# propose-and-approve proposal from a verified grounding — or carries a refusal.
ACTION_CALLS: list[tuple[dict[str, str], str]] = [
    (
        {
            "action": "incident",
            "domain": "devex",
            "question": "Why did run R-1042 fail, and has this happened before?",
        },
        "an incident drafted from a DevEx RCA — every field grounded and verified",
    ),
    (
        {
            "action": "pr_summary",
            "domain": "devex",
            "question": "What does PR-201 change?",
        },
        "a PR summary drafted from a change analysis",
    ),
    (
        {
            "action": "incident",
            "domain": "devex",
            "question": "What does PR-201 change?",
        },
        "a carried refusal — an incident asked from a PR question (incompatible route)",
    ),
]


def _truncate(text: str, limit: int = 160) -> str:
    text = text.replace("\n", " ").strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _render_action_catalog(result: dict[str, Any]) -> list[str]:
    return [
        f"  • {a['name']} (from {a['from_route']}; "
        f"domains {', '.join(a['domains'])}): {_truncate(a['description'], 110)}"
        for a in result["actions"]
    ]


def _render_action(result: dict[str, Any]) -> list[str]:
    lines = [
        f"  kind: {result['kind']}  route: {result['route']['kind']} — "
        f"{result['route']['reason']}",
        f"  grounded: {result['grounded']}  all_grounded: {result['all_grounded']}  "
        f"requires_approval: {result['requires_approval']}  "
        f"executed: {result['executed']}",
    ]
    if result["refused"]:
        lines.append(f"  refusal: {result['refusal']}")
        return lines
    for field in result["fields"]:
        lines.append(
            f"  field [verified={field['verified']}] {field['name']}: "
            f"{_truncate(field['value'], 100)}"
        )
    return lines


def _render_result(result: dict[str, Any]) -> list[str]:
    lines = [
        f"  route: {result['route']['kind']} — {result['route']['reason']}",
        f"  grounded: {result['grounded']}  refused: {result['refused']}  "
        f"all_verified: {result['all_verified']}",
    ]
    if result["refused"]:
        lines.append(f"  refusal: {result['refusal']}")
        return lines
    for i, claim in enumerate(result["claims"], start=1):
        lines.append(
            f"  claim {i} [verified={claim['verified']}]: {_truncate(claim['text'])}"
        )
        for ev in claim["support"]:
            lines.append(
                f"      ↳ {ev['id']}  ({ev['source']}; {ev['locator']['render']})"
            )
    return lines


async def _run() -> dict[str, Any]:
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "tessera.agent.mcp_server"]
    )
    captured: dict[str, Any] = {}
    async with (
        stdio_client(params) as (read, write),
        ClientSession(read, write) as session,
    ):
        init = await session.initialize()
        captured["server"] = {
            "name": init.serverInfo.name,
            "version": init.serverInfo.version,
        }
        listed = await session.list_tools()
        captured["tools"] = [
            {"name": t.name, "description": t.description} for t in listed.tools
        ]
        exchange: list[dict[str, Any]] = []
        for tool, args, why in CALLS:
            res = await session.call_tool(tool, args)
            exchange.append(
                {
                    "tool": tool,
                    "arguments": args,
                    "why": why,
                    "result": res.structuredContent,
                }
            )
        # One assertions call, keyed off a record the business answer cited.
        first = exchange[0]["result"]
        record_id = first["claims"][0]["support"][0]["id"]
        res = await session.call_tool(
            "assertions", {"domain": "business", "record_id": record_id}
        )
        exchange.append(
            {
                "tool": "assertions",
                "arguments": {"domain": "business", "record_id": record_id},
                "why": "the entity-resolution trail behind a cited record",
                "result": res.structuredContent,
            }
        )
        # The grounded-action tools (Milestone 12): discover the catalog, then draft.
        listed_actions = await session.call_tool("list_actions", {})
        exchange.append(
            {
                "tool": "list_actions",
                "arguments": {},
                "why": "the declared action catalog an agent can draft from",
                "result": listed_actions.structuredContent,
            }
        )
        for args, why in ACTION_CALLS:
            res = await session.call_tool("draft_action", args)
            exchange.append(
                {
                    "tool": "draft_action",
                    "arguments": args,
                    "why": why,
                    "result": res.structuredContent,
                }
            )
        captured["exchange"] = exchange
    return captured


def _write_transcript(captured: dict[str, Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "session.json").write_text(
        json.dumps(captured, indent=2, ensure_ascii=False) + "\n", "utf-8"
    )

    md: list[str] = [
        "# Tessera MCP session — a real client ↔ server exchange",
        "",
        "Captured by `uv run --extra agent python scripts/record_mcp_session.py`: a",
        "real MCP client driving the `tessera-mcp` server over stdio (specs 0084,",
        "0090). Not",
        "run in CI (no MCP SDK); the structured tool results are deterministic.",
        "",
        f"**Server:** `{captured['server']['name']}` "
        f"v`{captured['server']['version']}`",
        "",
        "## Tools advertised",
        "",
    ]
    for tool in captured["tools"]:
        md.append(f"- **`{tool['name']}`** — {_truncate(tool['description'], 200)}")
    md.append("")
    md.append("## The exchange")
    for step in captured["exchange"]:
        md.append("")
        args_json = json.dumps(step["arguments"], ensure_ascii=False)
        md.append(f"### → `{step['tool']}` {args_json}")
        md.append(f"_{step['why']}_")
        md.append("")
        if step["tool"] == "assertions":
            md.append(f"  record: {step['result']['record_id']}")
            for a in step["result"]["assertions"]:
                md.append(
                    f"  • {a['kind']} {a['a']} ↔ {a['b']} "
                    f"(confidence {a['confidence']}): {_truncate(a['reason'], 120)}"
                )
        elif step["tool"] == "list_actions":
            md.extend(_render_action_catalog(step["result"]))
        elif step["tool"] == "draft_action":
            md.extend(_render_action(step["result"]))
        else:
            md.extend(_render_result(step["result"]))
    md.append("")
    (OUT_DIR / "TRANSCRIPT.md").write_text("\n".join(md), "utf-8")


def main() -> None:
    captured = asyncio.run(_run())
    _write_transcript(captured)
    print(f"wrote {OUT_DIR / 'TRANSCRIPT.md'} and session.json")
    print(f"  tools: {[t['name'] for t in captured['tools']]}")
    print(f"  exchange steps: {len(captured['exchange'])}")


if __name__ == "__main__":
    main()
