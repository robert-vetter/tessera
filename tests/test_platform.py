"""The platform seam (spec 0039): local by default, cloud only by explicit config.

Everything here runs key-free and offline: a fake transport pins our side of
each provider's request contract (URLs, headers, payloads) and the
degradation rules — exactly what CI can honestly verify without provisioned
services (DEPLOYMENT.md states the rest).
"""

from __future__ import annotations

import pytest

from tessera.platform.config import (
    DEFAULT_ANTHROPIC_MODEL,
    PROVIDER_NONE,
    load_config,
)
from tessera.platform.providers import (
    AnthropicProvider,
    GenAIHubProvider,
    ProviderError,
    provider_from_env,
)


def test_default_is_local_mode_and_touches_nothing() -> None:
    """A fresh clone has no TESSERA_NARRATOR: provider is none, and
    provider_from_env returns None without any transport activity."""
    config = load_config(env={})
    assert config.provider == PROVIDER_NONE

    def exploding_transport(
        url: str, headers: dict[str, str], payload: dict[str, object]
    ) -> dict[str, object]:
        raise AssertionError("local mode must not construct a provider")

    assert provider_from_env(config, transport=exploding_transport) is None


def test_unknown_provider_fails_loudly() -> None:
    with pytest.raises(ValueError, match="TESSERA_NARRATOR"):
        load_config(env={"TESSERA_NARRATOR": "gpt-magic"})


def test_half_configured_genai_hub_fails_at_construction() -> None:
    config = load_config(
        env={"TESSERA_NARRATOR": "genai-hub", "AICORE_AUTH_URL": "https://auth"}
    )
    with pytest.raises(ProviderError, match="AICORE_CLIENT_ID"):
        provider_from_env(config)


def test_anthropic_requires_a_key() -> None:
    config = load_config(env={"TESSERA_NARRATOR": "anthropic"})
    with pytest.raises(ProviderError, match="ANTHROPIC_API_KEY"):
        provider_from_env(config)


def _genai_env() -> dict[str, str]:
    return {
        "TESSERA_NARRATOR": "genai-hub",
        "AICORE_AUTH_URL": "https://sub.authentication.sap.hana.ondemand.com",
        "AICORE_CLIENT_ID": "sb-client",
        "AICORE_CLIENT_SECRET": "secret",
        "AICORE_BASE_URL": "https://api.ai.prod.eu-central-1.aws.ml.hana.ondemand.com",
        "AICORE_RESOURCE_GROUP": "tessera",
        "TESSERA_GENAI_DEPLOYMENT": "d-123456",
    }


def test_genai_hub_request_contract() -> None:
    """Token from XSUAA (basic auth, client credentials), then chat completion
    against the deployment, in the configured resource group."""
    calls: list[tuple[str, dict[str, str], dict[str, object]]] = []

    def fake_transport(
        url: str, headers: dict[str, str], payload: dict[str, object]
    ) -> dict[str, object]:
        calls.append((url, headers, payload))
        if "/oauth/token" in url:
            return {"access_token": "tok-abc"}
        return {"choices": [{"message": {"content": "a narration"}}]}

    provider = provider_from_env(load_config(env=_genai_env()), fake_transport)
    assert provider is not None and provider.name == "sap-genai-hub"
    text = provider.complete("system rules", "the claims")
    assert text == "a narration"

    token_url, token_headers, _ = calls[0]
    assert token_url.endswith("/oauth/token?grant_type=client_credentials")
    assert token_headers["Authorization"].startswith("Basic ")

    infer_url, infer_headers, infer_payload = calls[1]
    assert infer_url == (
        "https://api.ai.prod.eu-central-1.aws.ml.hana.ondemand.com"
        "/v2/inference/deployments/d-123456/chat/completions"
    )
    assert infer_headers["Authorization"] == "Bearer tok-abc"
    assert infer_headers["AI-Resource-Group"] == "tessera"
    messages = infer_payload["messages"]
    assert isinstance(messages, list)
    assert [m["role"] for m in messages] == ["system", "user"]


def test_anthropic_request_contract() -> None:
    calls: list[tuple[str, dict[str, str], dict[str, object]]] = []

    def fake_transport(
        url: str, headers: dict[str, str], payload: dict[str, object]
    ) -> dict[str, object]:
        calls.append((url, headers, payload))
        return {"content": [{"type": "text", "text": "a narration"}]}

    config = load_config(
        env={"TESSERA_NARRATOR": "anthropic", "ANTHROPIC_API_KEY": "sk-test"}
    )
    provider = provider_from_env(config, fake_transport)
    assert provider is not None and provider.name == "anthropic"
    assert provider.complete("system rules", "the claims") == "a narration"

    url, headers, payload = calls[0]
    assert url == "https://api.anthropic.com/v1/messages"
    assert headers["x-api-key"] == "sk-test"
    assert "anthropic-version" in headers
    assert payload["model"] == DEFAULT_ANTHROPIC_MODEL
    assert payload["system"] == "system rules"


def test_protocol_breakage_degrades_to_provider_error() -> None:
    """Malformed upstream responses become ProviderError — the narration layer
    can always fall back to deterministic rendering (never a crash)."""

    def broken_transport(
        url: str, headers: dict[str, str], payload: dict[str, object]
    ) -> dict[str, object]:
        return {"unexpected": True}

    genai = GenAIHubProvider(
        config=load_config(env=_genai_env()), transport=broken_transport
    )
    with pytest.raises(ProviderError):
        genai.complete("s", "p")

    anthropic = AnthropicProvider(
        config=load_config(
            env={"TESSERA_NARRATOR": "anthropic", "ANTHROPIC_API_KEY": "k"}
        ),
        transport=broken_transport,
    )
    with pytest.raises(ProviderError):
        anthropic.complete("s", "p")
