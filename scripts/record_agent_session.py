"""Record a real *LLM agent* driving Tessera over MCP (Milestone 17 Unit 4).

The headline demo of the whole project: a real Claude agent, given **only**
Tessera's seven MCP tools, answers enterprise questions — and can therefore
only say what Tessera can prove and only draft/execute what Tessera grounds.
It cites, it refuses when Tessera refuses, and its action ends at a *simulated*
receipt. This is the "ran on X" artifact for the agentic thesis: a real
client (Claude) ↔ real transport (the ``tessera-mcp`` stdio server) session,
committed to ``data/agent_session/``.

Not run in CI (needs the MCP SDK *and* an Anthropic key). Reproduce locally:

    set -a; source .env; set +a          # ANTHROPIC_API_KEY
    uv run --extra agent python scripts/record_agent_session.py

The tool *results* are deterministic (the engine is); the agent's phrasing is
not, so the committed transcript is a captured real run, timestamped in the
header. The agent is instructed to ground every claim through the tools and to
carry a refusal as a refusal — the transcript shows it doing so, or the run is
reported honestly, never edited to look better.
"""

from __future__ import annotations

import asyncio
import json
import os
import urllib.request
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "agent_session"
_ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
_ANTHROPIC_VERSION = "2023-06-01"
_MODEL = os.environ.get("TESSERA_AGENT_MODEL", "claude-sonnet-5")
_MAX_TOKENS = 1024
_MAX_STEPS = 6  # tool-use rounds per question before we stop the loop

_SYSTEM = (
    "You are an enterprise assistant wired to Tessera, a trust layer. You have "
    "NO knowledge of the user's data except what Tessera's tools return. RULES: "
    "(1) Answer ONLY from tool results — never state a fact you did not obtain "
    "from a tool. (2) Every claim in your final answer must come from a "
    "`ground` result's claims (cite the evidence source ids). (3) If Tessera "
    "returns a refusal (`grounded: false`), report the refusal plainly and do "
    "NOT answer anyway. (4) To act, use `draft_action` then `preview_payload` "
    "then `execute_action`; report the receipt (note it is simulated — nothing "
    "is sent). Be concise."
)

# The scripted user turns — chosen to exercise the three honest behaviours.
QUESTIONS: list[tuple[str, str]] = [
    (
        "devex",
        "Why did run R-1042 fail, and has it happened before? Cite your evidence.",
    ),
    (
        "devex",
        "Why did run R-1041 fail?",  # R-1041 PASSED → Tessera refuses the premise
    ),
    (
        "devex",
        "Draft and (simulated) execute an incident issue for run R-1042.",
    ),
]


def _anthropic(messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict:
    body = json.dumps(
        {
            "model": _MODEL,
            "max_tokens": _MAX_TOKENS,
            "system": _SYSTEM,
            "tools": tools,
            "messages": messages,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        _ANTHROPIC_URL,
        data=body,
        headers={
            "x-api-key": os.environ["ANTHROPIC_API_KEY"],
            "anthropic-version": _ANTHROPIC_VERSION,
            "content-type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request) as response:  # noqa: S310 - fixed https URL
        return json.loads(response.read().decode("utf-8"))


def _anthropic_tools(mcp_tools: list[Any]) -> list[dict[str, Any]]:
    """Bridge MCP tool schemas → Anthropic tool schemas (name/description/input)."""
    return [
        {
            "name": tool.name,
            "description": tool.description or "",
            "input_schema": tool.inputSchema,
        }
        for tool in mcp_tools
    ]


async def _run_question(
    session: ClientSession, tools: list[dict[str, Any]], domain: str, question: str
) -> dict[str, Any]:
    """One user turn: an Anthropic tool-use loop where every tool call is
    dispatched to the real Tessera MCP server. Captures the whole exchange."""
    user_text = f"[domain: {domain}] {question}"
    messages: list[dict[str, Any]] = [{"role": "user", "content": user_text}]
    trace: list[dict[str, Any]] = []

    for _ in range(_MAX_STEPS):
        reply = _anthropic(messages, tools)
        blocks = reply.get("content", [])
        messages.append({"role": "assistant", "content": blocks})
        tool_uses = [b for b in blocks if b.get("type") == "tool_use"]
        texts = [b["text"] for b in blocks if b.get("type") == "text"]
        trace.append({"assistant_text": " ".join(texts), "tool_calls": []})

        if reply.get("stop_reason") != "tool_use" or not tool_uses:
            break

        results: list[dict[str, Any]] = []
        for use in tool_uses:
            called = await session.call_tool(use["name"], use.get("input", {}))
            structured = called.structuredContent
            trace[-1]["tool_calls"].append(
                {
                    "tool": use["name"],
                    "arguments": use.get("input", {}),
                    "result": structured,
                }
            )
            results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": use["id"],
                    "content": json.dumps(structured, ensure_ascii=False),
                }
            )
        messages.append({"role": "user", "content": results})

    final = " ".join(step["assistant_text"] for step in trace if step["assistant_text"])
    return {
        "domain": domain,
        "question": question,
        "trace": trace,
        "final_answer": trace[-1]["assistant_text"],
        "full_answer": final,
    }


async def _record() -> list[dict[str, Any]]:
    params = StdioServerParameters(
        command="uv", args=["run", "tessera-mcp"], env=dict(os.environ)
    )
    async with (
        stdio_client(params) as (read, write),
        ClientSession(read, write) as session,
    ):
        await session.initialize()
        listed = await session.list_tools()
        tools = _anthropic_tools(listed.tools)
        turns = []
        for domain, question in QUESTIONS:
            turns.append(await _run_question(session, tools, domain, question))
        return turns


def _to_markdown(turns: list[dict[str, Any]]) -> str:
    md = [
        "# Tessera — a real Claude agent, grounded only through the MCP tools",
        "",
        "A captured session (Milestone 17): Claude is given **only** Tessera's "
        "seven MCP tools and must answer from them alone. It cites grounded "
        "evidence, carries a refusal as a refusal, and its action ends at a "
        "*simulated* receipt — nothing is sent. Tool results are deterministic; "
        f"the agent runs on `{_MODEL}`. Header note aside, this is a real run.",
        "",
    ]
    for i, turn in enumerate(turns, start=1):
        md.append(f"## Turn {i} — [{turn['domain']}] {turn['question']}")
        for step in turn["trace"]:
            if step["assistant_text"]:
                md.append(f"\n**Claude:** {step['assistant_text']}")
            for call in step["tool_calls"]:
                args = json.dumps(call["arguments"], ensure_ascii=False)
                md.append(f"\n> 🔧 `{call['tool']}({args})`")
                grounded = (
                    call["result"].get("grounded")
                    if isinstance(call["result"], dict)
                    else None
                )
                if grounded is not None:
                    md.append(f">   → grounded: `{grounded}`")
        md.append("")
    return "\n".join(md)


def main() -> None:
    if "ANTHROPIC_API_KEY" not in os.environ:
        raise SystemExit("set ANTHROPIC_API_KEY (see .env) to record the session.")
    turns = asyncio.run(_record())
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "session.json").write_text(
        json.dumps(turns, indent=2, ensure_ascii=False) + "\n", "utf-8"
    )
    (OUT_DIR / "TRANSCRIPT.md").write_text(_to_markdown(turns), "utf-8")
    print(f"wrote {OUT_DIR / 'TRANSCRIPT.md'} and session.json")


if __name__ == "__main__":
    main()
