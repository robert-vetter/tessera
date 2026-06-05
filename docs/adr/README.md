# Architecture Decision Records

An ADR captures a single decision that is **expensive to reverse**, the context that forced it, and the alternatives that lost. We keep them so that the answer to "why is it built this way?" is always written down rather than reconstructed from memory.

## Rules
- One decision per record. Numbered sequentially: `0001-…`, `0002-…`.
- **Append-only.** A decision that no longer holds is marked `superseded by NNNN` — never edited away or deleted. The trail of changed minds is part of the value.
- Short and concrete. A record, not an essay.
- Create new ones with the `/adr` command, using `0000-template.md`.

## When to write one
- Choosing a storage or graph technology.
- Choosing how grounding / provenance works.
- Defining or changing an eval metric.
- Any structural choice that later code will depend on.

## Index
- [0001](0001-record-architecture-decisions.md) — Record architecture decisions
