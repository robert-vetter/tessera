"""The grounded-tool layer — Tessera as an enterprise agent's evidence oracle.

Read-only, deterministic, vertical-neutral tools that an AI agent can call to get
claims, claim-level provenance, and principled refusals as plain serializable data,
each live-verified at the boundary with the eval's own ``is_supported`` (ADR 0022).
The MCP server (``tessera-mcp``, Milestone 11 Unit 4) transports these; this layer
itself has no MCP / embedding / LLM dependency, so it stays pure-stdlib and CI-tested.
"""

from __future__ import annotations

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

__all__ = [
    "GroundedAssertion",
    "GroundedClaim",
    "GroundedDomain",
    "GroundedEvidence",
    "GroundedResult",
    "assertions",
    "available_domains",
    "domain",
    "ground",
    "serialize_answer",
    "verify_claims",
]
