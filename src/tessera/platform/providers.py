"""Model providers: SAP Generative AI Hub first, Anthropic as the local demo path.

Both adapters speak plain HTTPS via the stdlib (no SDK dependency — the
request shapes stay visible and the project keeps zero runtime
dependencies). Both are constructed **only** from explicit configuration;
:func:`provider_from_env` returns ``None`` in the default local mode, and
nothing in this module is imported on any deterministic answer path.

Failure is honest and contained: any transport or protocol problem raises
:class:`ProviderError`, and the caller (narration, spec 0040) falls back to
deterministic rendering — a missing narrator can never block a grounded
answer.

Targeted API versions (also stated in ``docs/DEPLOYMENT.md``):
SAP AI Core inference ``/v2/inference/deployments/{id}/chat/completions``
(GenAI Hub orchestration-compatible), OAuth2 client-credentials via XSUAA;
Anthropic Messages API ``2023-06-01``.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

from tessera.platform.config import (
    EMBEDDINGS_NONE,
    PROVIDER_GENAI_HUB,
    PROVIDER_NONE,
    PlatformConfig,
    load_config,
)

_TIMEOUT_SECONDS = 30
_ANTHROPIC_VERSION = "2023-06-01"
_MAX_TOKENS = 1024

# A transport is "POST this JSON to this URL with these headers, give me the
# parsed JSON back" — small enough to fake completely in tests.
Transport = Callable[[str, dict[str, str], dict[str, object]], dict[str, object]]


class ProviderError(RuntimeError):
    """A provider could not produce a completion (transport, auth, protocol)."""


class ModelProvider(Protocol):
    """The one thing the engine may ask a model for: text from a prompt.

    Deliberately narrow (ADR 0012): no tools, no streaming, no state — the
    deterministic engine owns facts and structure; a provider only ever
    rephrases what is already verified (ADR 0006 trigger 2).
    """

    @property
    def name(self) -> str: ...

    def complete(self, system: str, prompt: str) -> str: ...


def _http_post_json(
    url: str, headers: dict[str, str], payload: dict[str, object]
) -> dict[str, object]:
    """The default transport. Anything unexpected becomes ProviderError."""
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json", **headers}
    )
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
            parsed = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError) as error:
        raise ProviderError(f"request to {url} failed: {error}") from error
    if not isinstance(parsed, dict):
        raise ProviderError(f"unexpected non-object response from {url}")
    return parsed


def _xsuaa_token(config: PlatformConfig, transport: Transport) -> str:
    """An XSUAA OAuth2 access token via client-credentials.

    Shared by every GenAI Hub adapter (chat and embeddings): the AI Core auth
    flow is identical regardless of which inference endpoint follows it.
    """
    response = transport(
        f"{config.aicore_auth_url.rstrip('/')}/oauth/token"
        "?grant_type=client_credentials",
        {
            "Authorization": _basic_auth(
                config.aicore_client_id, config.aicore_client_secret
            )
        },
        {},
    )
    token = response.get("access_token")
    if not isinstance(token, str) or not token:
        raise ProviderError("XSUAA token response carried no access_token")
    return token


@dataclass(frozen=True)
class GenAIHubProvider:
    """SAP Generative AI Hub (on AI Core) — the documented production target.

    OAuth2 client-credentials against the subaccount's XSUAA, then chat
    completions against a GenAI Hub deployment in the configured resource
    group. Requires a provisioned deployment (see the DEPLOYMENT.md runbook);
    in this repository it is exercised against a fake transport only — stated
    honestly there.
    """

    config: PlatformConfig
    transport: Transport = _http_post_json

    @property
    def name(self) -> str:
        return "sap-genai-hub"

    def complete(self, system: str, prompt: str) -> str:
        url = (
            f"{self.config.aicore_base_url.rstrip('/')}/v2/inference/deployments/"
            f"{self.config.genai_deployment_id}/chat/completions"
        )
        response = self.transport(
            url,
            {
                "Authorization": f"Bearer {_xsuaa_token(self.config, self.transport)}",
                "AI-Resource-Group": self.config.aicore_resource_group,
            },
            {
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": _MAX_TOKENS,
            },
        )
        try:
            choices = response["choices"]
            assert isinstance(choices, list)
            message = choices[0]["message"]["content"]
        except (KeyError, IndexError, TypeError, AssertionError) as error:
            raise ProviderError(f"unexpected completion shape: {error}") from error
        if not isinstance(message, str):
            raise ProviderError("completion content was not text")
        return message


@dataclass(frozen=True)
class AnthropicProvider:
    """The Anthropic Messages API — narration demoable on a laptop today
    (maintainer decision, spec 0035): same protocol surface, one env key."""

    config: PlatformConfig
    transport: Transport = _http_post_json

    @property
    def name(self) -> str:
        return "anthropic"

    def complete(self, system: str, prompt: str) -> str:
        response = self.transport(
            "https://api.anthropic.com/v1/messages",
            {
                "x-api-key": self.config.anthropic_api_key,
                "anthropic-version": _ANTHROPIC_VERSION,
            },
            {
                "model": self.config.anthropic_model,
                "max_tokens": _MAX_TOKENS,
                "system": system,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        try:
            blocks = response["content"]
            assert isinstance(blocks, list)
            text = "".join(
                str(block["text"])
                for block in blocks
                if isinstance(block, dict) and block.get("type") == "text"
            )
        except (KeyError, TypeError, AssertionError) as error:
            raise ProviderError(f"unexpected message shape: {error}") from error
        if not text:
            raise ProviderError("message carried no text blocks")
        return text


def _basic_auth(client_id: str, client_secret: str) -> str:
    import base64

    raw = f"{client_id}:{client_secret}".encode()
    return "Basic " + base64.b64encode(raw).decode("ascii")


def provider_from_env(
    config: PlatformConfig | None = None, transport: Transport = _http_post_json
) -> ModelProvider | None:
    """The configured provider, or ``None`` in the (default) local mode.

    Construction validates that the selected provider's required settings are
    present — a half-configured provider fails loudly here, not mid-answer.
    """
    cfg = load_config() if config is None else config
    if cfg.provider == PROVIDER_NONE:
        return None
    if cfg.provider == PROVIDER_GENAI_HUB:
        missing = [
            name
            for name, value in (
                ("AICORE_AUTH_URL", cfg.aicore_auth_url),
                ("AICORE_CLIENT_ID", cfg.aicore_client_id),
                ("AICORE_CLIENT_SECRET", cfg.aicore_client_secret),
                ("AICORE_BASE_URL", cfg.aicore_base_url),
                ("TESSERA_GENAI_DEPLOYMENT", cfg.genai_deployment_id),
            )
            if not value
        ]
        if missing:
            raise ProviderError(f"genai-hub selected but unset: {', '.join(missing)}")
        return GenAIHubProvider(config=cfg, transport=transport)
    if not cfg.anthropic_api_key:
        raise ProviderError("anthropic selected but ANTHROPIC_API_KEY is unset")
    return AnthropicProvider(config=cfg, transport=transport)


# --- Embeddings: text → dense vector for semantic retrieval (ADR 0015) -------
#
# A separate, equally narrow seam. Embeddings serve RETRIEVAL ONLY — they change
# what evidence is surfaced, never what is claimed. The faithfulness verifier
# (eval/metrics.py) imports nothing from here; a leak-guard test pins that, so a
# 1.0 stays earned by structure, not by a model.


class EmbeddingProvider(Protocol):
    """The one thing the engine may ask an embedding model for: vectors.

    Batch by design — indexing embeds many records in one call. Deliberately
    narrow (ADR 0015), mirroring :class:`ModelProvider`.
    """

    @property
    def name(self) -> str: ...

    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


def _parse_embeddings(
    response: dict[str, object], *, expected: int
) -> list[list[float]]:
    """Parse an OpenAI-shaped embeddings response into input-ordered vectors.

    Both Azure- and OpenAI-style GenAI Hub deployments return
    ``{"data": [{"index": i, "embedding": [...]}, ...]}``; the list may arrive
    out of order, so we sort by ``index``. Anything unexpected becomes a
    :class:`ProviderError` so the caller degrades rather than indexing garbage.
    """
    try:
        data = response["data"]
        assert isinstance(data, list)
        ordered = sorted(data, key=lambda item: int(item["index"]))
        vectors = [[float(x) for x in item["embedding"]] for item in ordered]
    except (KeyError, IndexError, TypeError, ValueError, AssertionError) as error:
        raise ProviderError(f"unexpected embeddings shape: {error}") from error
    if len(vectors) != expected:
        raise ProviderError(f"expected {expected} embedding(s), got {len(vectors)}")
    return vectors


@dataclass(frozen=True)
class GenAIHubEmbeddingProvider:
    """SAP Generative AI Hub embeddings — text → dense vector (ADR 0015).

    Same XSUAA auth and base URL as the chat adapter; a different inference
    suffix (configurable — see ``genai_embedding_path``). Returns one vector per
    input text, in input order. Exercised against a fake transport in this
    repository; a live smoke test precedes the one recorded online run
    (DEPLOYMENT.md / spec 0057).
    """

    config: PlatformConfig
    transport: Transport = _http_post_json

    @property
    def name(self) -> str:
        return "sap-genai-hub-embeddings"

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        url = (
            f"{self.config.aicore_base_url.rstrip('/')}/v2/inference/deployments/"
            f"{self.config.genai_embedding_deployment_id}/"
            f"{self.config.genai_embedding_path.strip('/')}"
        )
        response = self.transport(
            url,
            {
                "Authorization": f"Bearer {_xsuaa_token(self.config, self.transport)}",
                "AI-Resource-Group": self.config.aicore_resource_group,
            },
            {"input": list(texts)},
        )
        return _parse_embeddings(response, expected=len(texts))


def embedding_provider_from_env(
    config: PlatformConfig | None = None, transport: Transport = _http_post_json
) -> EmbeddingProvider | None:
    """The configured embedding provider, or ``None`` in the (default) local mode.

    Independent of the narrator. A half-configured provider fails loudly here,
    naming the missing variable — not mid-index.
    """
    cfg = load_config() if config is None else config
    if cfg.embeddings == EMBEDDINGS_NONE:
        return None
    missing = [
        name
        for name, value in (
            ("AICORE_AUTH_URL", cfg.aicore_auth_url),
            ("AICORE_CLIENT_ID", cfg.aicore_client_id),
            ("AICORE_CLIENT_SECRET", cfg.aicore_client_secret),
            ("AICORE_BASE_URL", cfg.aicore_base_url),
            ("TESSERA_GENAI_EMBEDDING_DEPLOYMENT", cfg.genai_embedding_deployment_id),
        )
        if not value
    ]
    if missing:
        raise ProviderError(
            f"genai-hub embeddings selected but unset: {', '.join(missing)}"
        )
    return GenAIHubEmbeddingProvider(config=cfg, transport=transport)
