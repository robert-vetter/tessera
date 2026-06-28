# 0080. Close Milestone 10 — registration-key entity resolution

- **Phase / milestone:** Milestone 10 — registration/tax-key entity resolution
- **Issue:** —
- **Status:** approved (autonomous mode; the milestone close)

## What this unit does

The documentation + release close for Milestone 10. No engine or data change.

1. **Frozen-core empty-diff audit** (`milestone-9..HEAD`): `resolution.py`,
   `retrieval.py`, `routing.py`, `grounding.py`, `ingestion.py`, `eval/metrics.py` all
   **empty-diff**; the only engine delta is `graph.py` (+32/−22 — the bridge-reason
   wording generalization + docstrings, behaviour-preserving), plus the sanctioned
   source delta (`sources/salt.py`) and the vertical opt-in (`business/knowledge.py`).
   The leak-guard holds (the verifier's import closure unchanged).
2. **WRITEUP** — the Milestone-10 section (the floor, the zero-logic-change key, the
   measured 0.909 → 1.000 close, the new registry-only floor, the BM25 near-tie
   disclosure); updated ER limitation + future-work; an 8th "what was learned".
3. **README** — the ER section (key + address two-way gate, ADR 0020) and the milestone
   summary line; numbers refreshed.
4. **CHANGELOG** — `[milestone-10]`.
5. **ADR nav/index** — ADR 0020 added to `docs/adr/README.md` and `mkdocs.yml`.
6. **STATUS** — this milestone's journal entry.
7. **Tag** `milestone-10`; memory; next-milestone kickoff.

## Acceptance criteria

- [x] Empty-diff core audit run; the one engine delta (`graph.py` wording) documented.
- [x] WRITEUP / README / CHANGELOG / ADR index + nav / STATUS reflect M10.
- [x] Gate green under multiple `PYTHONHASHSEED` values; faithfulness 1.0 all batteries.
- [x] Tag `milestone-10`; memory updated; kickoff handed back.

## Out of scope

- The heading-chunk retrieval root cause (filed as a follow-up task in Unit 3).
- The next milestone (defined with the maintainer).
