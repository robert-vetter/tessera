# Gold sets

Curated, human-checked evaluation cases — one `*.json` file per case, one
directory per measured vertical (battery, see
[`docs/adr/0009-multi-vertical-eval-batteries.md`](../../docs/adr/0009-multi-vertical-eval-batteries.md)) —
that `tessera.eval` scores into faithfulness / coverage / quality (see
[`docs/adr/0005-faithfulness-metric.md`](../../docs/adr/0005-faithfulness-metric.md)).
Small and hand-curated on purpose, so every number stays auditable.

Case format:

```json
{
  "id": "unique_id",
  "question": "...",
  "engine": "an answer path of the owning vertical, e.g. compose | retrieve | route | rca | summary",
  "kind": "answer" | "refuse",
  "expected_support": ["evidence record ids a faithful answer should surface"],
  "expected_facts": ["substrings a correct answer must contain"]
}
```

- **`business/`** — the Business Data Copilot cases (Phase 1/2): cross-source
  composition (Müller), a retrieval lookup, the Lumière billing case, the
  Atlas mixed-currency refuse-to-sum, ambiguous and out-of-scope refusals,
  and the renewal-date conflict.
- **`devex/`** — the DevEx Copilot cases (Phase 3): root-cause analysis with
  recurrence, PR change-summaries, and this vertical's refusals — including
  its *named* coverage misses, kept so the number stays honest.

`expected_facts` and `expected_support` are checked against the answer the
engine actually produces. Faithfulness is gated (must be 1.0) for **every**
battery, gold and synthetic alike; coverage and quality are reported as
honest, improvable targets.
