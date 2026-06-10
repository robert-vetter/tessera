"""The SAP platform seam — cloud as configuration, local as the default.

Tessera runs clone-and-run, offline, with no keys (the portable local mode
every ADR protects). This package is the documented opt-in to SAP's AI
infrastructure (spec 0039 / ADR 0012, design in ``docs/DEPLOYMENT.md``):

- :mod:`tessera.platform.config` reads the environment into a
  :class:`~tessera.platform.config.PlatformConfig`; with nothing set, the
  provider is ``none`` and no code path touches the network.
- :mod:`tessera.platform.providers` defines the :class:`ModelProvider`
  protocol and two adapters — **SAP Generative AI Hub** (on AI Core, the
  production target) and the **Anthropic API** (the locally demoable
  fallback) — both pure stdlib HTTP, both constructed only from explicit
  configuration.

The provider's only consumer is narration (ADR 0006 trigger 2, spec 0040):
an LLM may rephrase verifier-checked claims; it never generates facts.
"""

from tessera.platform.config import PlatformConfig, load_config
from tessera.platform.providers import (
    ModelProvider,
    ProviderError,
    provider_from_env,
)

__all__ = [
    "ModelProvider",
    "PlatformConfig",
    "ProviderError",
    "load_config",
    "provider_from_env",
]
