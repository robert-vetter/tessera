# Reproducible development image for Tessera: pinned Python 3.12 + uv, with the
# exact dependency set from uv.lock. Lets anyone clone and run the gate
# identically, with no host toolchain assumed (docs/ENGINEERING.md §3).
#
# Build:  docker build -t tessera-dev .
# Use:    docker run --rm -it tessera-dev            # shell
#         docker run --rm tessera-dev uv run pytest  # run the gate
#
# Base image is pinned by digest (supply-chain hygiene, matching the SHA-pinned
# CI actions); dependabot's docker ecosystem keeps it current.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim@sha256:e5b65587bce7de595f299855d7385fe7fca39b8a74baa261ba1b7147afa78e58

# uv container hygiene: compile bytecode for faster startup, and copy (not link)
# from the cache since the build layer and the venv are on different mounts.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /workspace

# Install dependencies first, in their own layer, so they are cached unless the
# manifests change. --no-install-project: deps only, not the app yet.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-install-project

# Now copy the source and install the project itself into the same environment.
COPY . .
RUN uv sync --frozen

# Put the project's virtualenv on PATH so `python`, `ruff`, `pytest`, etc. work
# directly (no `uv run` prefix needed) inside the container.
ENV PATH="/workspace/.venv/bin:$PATH"

# Run as a non-root user (uid 1000, conventional devcontainer name) that owns
# the workspace.
RUN useradd --create-home --uid 1000 vscode \
    && chown -R vscode:vscode /workspace
USER vscode

CMD ["bash"]
