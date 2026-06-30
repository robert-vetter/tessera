"""The grounded-tool layer — Tessera as an enterprise agent's evidence oracle.

Read-only, deterministic, vertical-neutral tools that an AI agent can call to get
claims, claim-level provenance, and principled refusals as plain serializable data,
each live-verified at the boundary with the eval's own ``is_supported`` (ADR 0022).
The MCP server (``tessera-mcp``, Milestone 11 Unit 4) transports these; this layer
itself has no MCP / embedding / LLM dependency, so it stays pure-stdlib and CI-tested.
"""

from __future__ import annotations

from tessera.agent.actions import (
    ActionField,
    ActionProposal,
    available_action_names,
    available_actions,
    draft_action,
)
from tessera.agent.grounded import (
    GroundedAssertion,
    GroundedClaim,
    GroundedDomain,
    GroundedEvidence,
    GroundedResult,
    assertions,
    available_domains,
    domain,
    ground,
    serialize_answer,
    verify_claims,
)
from tessera.agent.payloads import (
    PayloadSlot,
    RenderedPayload,
    available_payload_targets,
    preview_payload,
    render_payload,
)

__all__ = [
    "ActionField",
    "ActionProposal",
    "GroundedAssertion",
    "GroundedClaim",
    "GroundedDomain",
    "GroundedEvidence",
    "GroundedResult",
    "PayloadSlot",
    "RenderedPayload",
    "assertions",
    "available_action_names",
    "available_actions",
    "available_domains",
    "available_payload_targets",
    "domain",
    "draft_action",
    "ground",
    "preview_payload",
    "render_payload",
    "serialize_answer",
    "verify_claims",
]
