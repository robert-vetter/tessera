---
title: Tessera — ask with proof
emoji: 🧩
colorFrom: blue
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: Every claim proven, every action approved — with receipts.
---

# Tessera — a trust layer for enterprise AI agents (live demo)

Ask a question over enterprise data — tables, documents, CI logs. Every claim
in the answer traces to the exact records that support it; what cannot be
proven is **refused**, and any action ends in a **receipt** (simulated here —
this demo holds no credentials and can send nothing).

- Source & write-up: https://github.com/robert-vetter/tessera
- A real Claude agent grounded only through Tessera's MCP tools:
  https://github.com/robert-vetter/tessera/blob/main/data/agent_session/TRANSCRIPT.md
- The one real, approval-gated send, on the record:
  https://github.com/robert-vetter/tessera-exec-oneshot/issues/1

This Space builds the repo's `main` branch (`deploy/hf-space/Dockerfile`).
Update it via *Settings → Factory rebuild*.
