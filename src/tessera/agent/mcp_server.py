"""The MCP server — Tessera's grounded tools over the Model Context Protocol.

A *thin transport*: it serializes the grounded-tool layer
(:mod:`tessera.agent.grounded`, ADR 0022), the grounded-action layer
(:mod:`tessera.agent.actions`, ADR 0023), and the dry-run payload renderer
(:mod:`tessera.agent.payloads`, ADR 0024) over MCP so an enterprise AI agent — Claude,
or any MCP client — can call Tessera as its evidence oracle, ask it to draft grounded
propose-and-approve actions, *and* preview the exact request those actions would send.
It contains **no grounding, drafting, or rendering logic**: every answer, verdict,
refusal, drafted field, and rendered payload comes from those layers, and nothing is
executed — ``draft_action`` returns a proposal a human or agent approves, and
``preview_payload`` renders the wire request without sending it.

The MCP SDK is the opt-in ``agent`` extra (``uv sync --extra agent``), imported
**lazily** only inside :func:`build_server` / :func:`main`. Importing this module —
and the whole default clone-and-run graph — pulls no ``mcp`` dependency (pinned by
``tests/test_mcp_server.py``); the grounded-tool substance carries none either.

The server is split in two so the substance is testable in CI without the SDK:
the MCP-free ``tool_*`` handlers (below) are unit-tested directly; the SDK wiring in
:func:`build_server` is contract-tested where the extra is installed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from tessera.agent.actions import available_actions, draft_action
from tessera.agent.grounded import assertions, available_domains, domain, ground
from tessera.agent.payloads import preview_payload

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

SERVER_NAME = "tessera"
SERVER_INSTRUCTIONS = (
    "Tessera is a trust layer: it answers questions over enterprise data with "
    "claim-level provenance and refuses when evidence is insufficient. Every claim "
    "returned is live-verified against its cited evidence (a structural faithfulness "
    "check); a refusal is explicit and must never be treated as an answer. Call "
    "list_domains to see what you can ask about, ground to get a verified answer with "
    "provenance, and assertions to inspect why two records were linked. To act on an "
    "answer, call list_actions to see the draftable actions and draft_action to get a "
    "grounded, cited PROPOSAL whose every field is verifier-checked, then "
    "preview_payload to render the EXACT external request that proposal would send (a "
    "GitHub create-issue or PR comment) — every value field-grounded. Propose-and-"
    "approve only: Tessera drafts and renders, a human or agent approves and sends; "
    "nothing is executed and nothing is sent."
)


# --- MCP-free tool handlers (unit-tested in CI without the SDK) ----------------


def tool_list_domains() -> dict[str, object]:
    """The domains an agent can ground a question in, with descriptions."""
    return {
        "domains": [
            {"name": dom.name, "description": dom.description}
            for dom in (domain(name) for name in available_domains())
        ]
    }


def tool_ground(domain_name: str, question: str) -> dict[str, object]:
    """Ground ``question`` in ``domain_name`` and return the serialized result."""
    return ground(domain_name, question).to_dict()


def tool_assertions(domain_name: str, record_id: str) -> dict[str, object]:
    """The additive ER assertions (resolutions/mentions) touching ``record_id``."""
    return {
        "record_id": record_id,
        "assertions": [item.to_dict() for item in assertions(domain_name, record_id)],
    }


def tool_list_actions() -> dict[str, object]:
    """The actions an agent can draft, each with the domains and route it draws from."""
    return {"actions": available_actions()}


def tool_draft_action(action: str, domain: str, question: str) -> dict[str, object]:
    """Draft a grounded, field-verified, propose-and-approve action — or carry a
    refusal — for ``question`` in ``domain``. Holds no logic: it delegates verbatim
    to the Unit-3 grounded-action layer."""
    return draft_action(action, domain, question).to_dict()


def tool_preview_payload(action: str, domain: str, question: str) -> dict[str, object]:
    """Render the exact GitHub request a grounded action would send — or carry a
    withheld result — for ``question`` in ``domain``. Holds no logic: it delegates
    verbatim to the payload renderer (ADR 0024). Nothing is sent (``sent`` is false)."""
    return preview_payload(action, domain, question).to_dict()


# --- the MCP wiring (lazily imports the SDK) ----------------------------------

_GROUND_DESC = (
    "Answer a question over a Tessera domain and return grounded, cited claims — or "
    "a principled refusal. Each claim carries its full provenance inline (the cited "
    "record id, source, locator, and text) and a 'verified' verdict from the same "
    "structural faithfulness check the eval gates on. If 'refused' is true, "
    "'refusal' explains why and 'claims' is empty — do NOT treat a refusal as an "
    "answer. 'route' names which deterministic path answered and why. Args: domain "
    "(one of list_domains), question (natural language)."
)
_ASSERTIONS_DESC = (
    "Inspect the entity-resolution provenance touching a cited record: the additive, "
    "reversible resolution/mention assertions (with their reason and confidence) that "
    "say why two records were linked as the same real-world entity. Args: domain, "
    "record_id (an id from a ground() result's claim support)."
)
_LIST_DOMAINS_DESC = (
    "List the Tessera domains you can ground a question in, each with a description "
    "of what it covers. Call this first to choose a domain for ground()."
)
_LIST_ACTIONS_DESC = (
    "List the actions you can draft from a grounded answer, each with the domains and "
    "the route (e.g. an RCA, a change-summary) it draws from. Call this to choose an "
    "action for draft_action()."
)
_DRAFT_ACTION_DESC = (
    "Draft a grounded, cited action PROPOSAL from an answer — never an executed "
    "action. Tessera grounds the question, then maps the verified claims into "
    "role-labeled fields, each carrying its provenance and a 'verified' verdict (the "
    "same structural faithfulness check the eval gates on); 'all_grounded' is true "
    "only when every field is verifier-passing. If the grounding refused or routed "
    "incompatibly (e.g. asking for an incident from a PR question), 'refused' is true "
    "with a reason and 'fields' is empty — a refusal is never drafted into an action. "
    "'requires_approval' is always true and 'executed' always false: propose-and-"
    "approve, a human or agent approves and acts outside Tessera. Args: action (one of "
    "list_actions), domain, question."
)
_PREVIEW_PAYLOAD_DESC = (
    "Render the EXACT external request a grounded action would send — a dry-run "
    "preview, never sent. Tessera drafts the action, then maps its VERIFIED fields "
    "into the GitHub wire request (a create-issue for an incident, a PR comment for a "
    "pr_summary): 'request' carries the method, path, and JSON body; every content "
    "value traces to a verifier-passing field via 'slots' (each with its provenance "
    "and 'verified' verdict); 'all_grounded' is true only when every slot is "
    "verifier-passing. {owner}/{repo} stay unbound placeholders you fill at send "
    "time. If the grounding refused, routed incompatibly, or any field is unverified, "
    "'rendered' is false with 'withheld_reason' and no request — a payload is never "
    "rendered over ungrounded ground. 'sent' is ALWAYS false and 'requires_approval' "
    "always true: Tessera renders, a human or agent approves and sends. Args: action "
    "(one of list_actions), domain, question."
)


def build_server() -> FastMCP:
    """Build the MCP server exposing Tessera's grounded tools and action drafters.

    Lazily imports the MCP SDK (the opt-in ``agent`` extra), so the default import
    graph stays SDK-free. Registers the MCP-free handlers above as MCP tools; the
    server holds no grounding or drafting logic.
    """
    from mcp.server.fastmcp import FastMCP

    server: FastMCP = FastMCP(SERVER_NAME, instructions=SERVER_INSTRUCTIONS)

    @server.tool(name="list_domains", description=_LIST_DOMAINS_DESC)
    def _list_domains() -> dict[str, object]:
        return tool_list_domains()

    @server.tool(name="ground", description=_GROUND_DESC)
    def _ground(domain: str, question: str) -> dict[str, object]:
        return tool_ground(domain, question)

    @server.tool(name="assertions", description=_ASSERTIONS_DESC)
    def _assertions(domain: str, record_id: str) -> dict[str, object]:
        return tool_assertions(domain, record_id)

    @server.tool(name="list_actions", description=_LIST_ACTIONS_DESC)
    def _list_actions() -> dict[str, object]:
        return tool_list_actions()

    @server.tool(name="draft_action", description=_DRAFT_ACTION_DESC)
    def _draft_action(action: str, domain: str, question: str) -> dict[str, object]:
        return tool_draft_action(action, domain, question)

    @server.tool(name="preview_payload", description=_PREVIEW_PAYLOAD_DESC)
    def _preview_payload(action: str, domain: str, question: str) -> dict[str, object]:
        return tool_preview_payload(action, domain, question)

    return server


def main() -> None:
    """Run the Tessera MCP server over stdio (the ``tessera-mcp`` entry point)."""
    build_server().run("stdio")


if __name__ == "__main__":  # `python -m tessera.agent.mcp_server`
    main()
