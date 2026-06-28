"""The MCP server — Tessera's grounded tools over the Model Context Protocol.

A *thin transport* (ADR 0022): it serializes the read-only grounded-tool layer
(:mod:`tessera.agent.grounded`) over MCP so an enterprise AI agent — Claude, or any
MCP client — can call Tessera as its evidence oracle. It contains **no grounding
logic**: every answer, verdict, and refusal comes from the Unit-3 layer.

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

from tessera.agent.grounded import assertions, available_domains, domain, ground

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

SERVER_NAME = "tessera"
SERVER_INSTRUCTIONS = (
    "Tessera is a trust layer: it answers questions over enterprise data with "
    "claim-level provenance and refuses when evidence is insufficient. Every claim "
    "returned is live-verified against its cited evidence (a structural faithfulness "
    "check); a refusal is explicit and must never be treated as an answer. Call "
    "list_domains to see what you can ask about, ground to get a verified answer with "
    "provenance, and assertions to inspect why two records were linked."
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


def build_server() -> FastMCP:
    """Build the MCP server exposing Tessera's read-only grounded tools.

    Lazily imports the MCP SDK (the opt-in ``agent`` extra), so the default import
    graph stays SDK-free. Registers the MCP-free handlers above as MCP tools; the
    server holds no grounding logic.
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

    return server


def main() -> None:
    """Run the Tessera MCP server over stdio (the ``tessera-mcp`` entry point)."""
    build_server().run("stdio")


if __name__ == "__main__":  # `python -m tessera.agent.mcp_server`
    main()
