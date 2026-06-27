"""Platform configuration, read from the environment — nothing else.

One function (:func:`load_config`) turns environment variables into a frozen
:class:`PlatformConfig`. The default is always the portable local mode:
``provider="none"`` unless ``TESSERA_NARRATOR`` says otherwise, so a fresh
clone never needs (or touches) a key. The variable names follow SAP AI
Core's conventional ``AICORE_*`` family for the GenAI Hub side; the full
reference table lives in ``docs/DEPLOYMENT.md``.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

# Provider selector values for TESSERA_NARRATOR.
PROVIDER_NONE = "none"
PROVIDER_GENAI_HUB = "genai-hub"
PROVIDER_ANTHROPIC = "anthropic"

_VALID_PROVIDERS = frozenset({PROVIDER_NONE, PROVIDER_GENAI_HUB, PROVIDER_ANTHROPIC})

# Embedding selector values for TESSERA_EMBEDDINGS (ADR 0015). Independent of
# the narrator: a deployment may use semantic retrieval without narration.
EMBEDDINGS_NONE = "none"
EMBEDDINGS_GENAI_HUB = "genai-hub"

_VALID_EMBEDDINGS = frozenset({EMBEDDINGS_NONE, EMBEDDINGS_GENAI_HUB})

# A deliberately small, cost-conscious default for narration; overridable.
DEFAULT_ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"


@dataclass(frozen=True)
class PlatformConfig:
    """Everything the platform seam may need, resolved once."""

    provider: str  # one of the PROVIDER_* values
    # --- SAP Generative AI Hub (on AI Core), OAuth2 client credentials ----
    aicore_auth_url: str = ""
    aicore_client_id: str = ""
    aicore_client_secret: str = ""
    aicore_base_url: str = ""
    aicore_resource_group: str = "default"
    genai_deployment_id: str = ""
    # --- Anthropic API (the locally demoable fallback) ---------------------
    anthropic_api_key: str = ""
    anthropic_model: str = DEFAULT_ANTHROPIC_MODEL
    # --- Embeddings: GenAI Hub for semantic retrieval (ADR 0015) -----------
    embeddings: str = EMBEDDINGS_NONE
    genai_embedding_deployment_id: str = ""
    # The inference suffix differs by deployed model type (Azure-style
    # ``embeddings`` vs OpenAI-style ``v1/embeddings``); overridable so the
    # one-shot online run is never blocked by a URL suffix (spec 0052).
    genai_embedding_path: str = "embeddings"


def load_config(env: Mapping[str, str] | None = None) -> PlatformConfig:
    """Resolve the platform configuration from ``env`` (default: ``os.environ``).

    Unknown ``TESSERA_NARRATOR`` values raise immediately — a misspelled
    provider should fail loudly at startup, not silently disable narration.
    """
    variables = os.environ if env is None else env
    provider = variables.get("TESSERA_NARRATOR", PROVIDER_NONE).strip().lower()
    if provider not in _VALID_PROVIDERS:
        raise ValueError(
            f"TESSERA_NARRATOR must be one of {sorted(_VALID_PROVIDERS)}, "
            f"got {provider!r}"
        )
    embeddings = variables.get("TESSERA_EMBEDDINGS", EMBEDDINGS_NONE).strip().lower()
    if embeddings not in _VALID_EMBEDDINGS:
        raise ValueError(
            f"TESSERA_EMBEDDINGS must be one of {sorted(_VALID_EMBEDDINGS)}, "
            f"got {embeddings!r}"
        )
    return PlatformConfig(
        provider=provider,
        aicore_auth_url=variables.get("AICORE_AUTH_URL", ""),
        aicore_client_id=variables.get("AICORE_CLIENT_ID", ""),
        aicore_client_secret=variables.get("AICORE_CLIENT_SECRET", ""),
        aicore_base_url=variables.get("AICORE_BASE_URL", ""),
        aicore_resource_group=variables.get("AICORE_RESOURCE_GROUP", "default"),
        genai_deployment_id=variables.get("TESSERA_GENAI_DEPLOYMENT", ""),
        anthropic_api_key=variables.get("ANTHROPIC_API_KEY", ""),
        anthropic_model=variables.get(
            "TESSERA_ANTHROPIC_MODEL", DEFAULT_ANTHROPIC_MODEL
        ),
        embeddings=embeddings,
        genai_embedding_deployment_id=variables.get(
            "TESSERA_GENAI_EMBEDDING_DEPLOYMENT", ""
        ),
        genai_embedding_path=variables.get(
            "TESSERA_GENAI_EMBEDDING_PATH", "embeddings"
        ),
    )
