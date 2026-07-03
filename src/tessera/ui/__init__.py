"""The web surface — one page over the existing trust objects (Milestone 17).

Pure stdlib (``http.server``), zero JavaScript, zero new dependencies: the UI
is a strict *consumer* of the agent boundary (``GroundedResult`` →
``ActionProposal`` → ``RenderedPayload`` → ``ExecutionReceipt``) and renders
what the engine proved — it grounds nothing, verifies nothing, and holds no
credential (ADR 0027).
"""
