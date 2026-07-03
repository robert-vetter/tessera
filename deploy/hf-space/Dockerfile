# Tessera demo — Hugging Face Docker Space (key-free, read-only, no credentials).
#
# Builds the public Tessera repo's `main` branch and serves the stdlib web UI on
# the Space's expected port (7860; see README.md `app_port`). The UI holds no
# credential and its action flow is simulated-only by construction (ADR 0027),
# so a public instance can neither send anything nor leak anything.
#
# Update a running Space with Settings → Factory rebuild (re-pulls `main`).
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim@sha256:e5b65587bce7de595f299855d7385fe7fca39b8a74baa261ba1b7147afa78e58

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# HF Spaces run the container as UID 1000 "user" — set it up before any copy.
RUN useradd --create-home --uid 1000 user
USER user
ENV HOME=/home/user
WORKDIR /home/user/app

# Fetch the repo source without needing git in the slim image (ADD from URL).
ADD --chown=user https://github.com/robert-vetter/tessera/archive/refs/heads/main.tar.gz /tmp/src.tar.gz
RUN tar -xzf /tmp/src.tar.gz --strip-components=1 && rm /tmp/src.tar.gz

# Install the project (zero runtime deps; --no-dev skips the test/docs toolchain).
# The editable install keeps data/ and eval/ resolvable at their repo-root paths.
RUN uv sync --frozen --no-dev

# Put the venv on PATH so the entry point runs directly (no `uv run` at runtime).
ENV PATH="/home/user/app/.venv/bin:$PATH"

EXPOSE 7860
CMD ["tessera-ui", "--host", "0.0.0.0", "--port", "7860"]
