# Gold set

Curated, human-checked evaluation cases — one `*.json` file per case — that
`tessera.eval` scores into faithfulness / coverage / quality (see
[`docs/adr/0005-faithfulness-metric.md`](../../docs/adr/0005-faithfulness-metric.md)).
Small and hand-curated on purpose, so every number stays auditable.

Case format:

```json
{
  "id": "unique_id",
  "question": "...",
  "engine": "compose" | "retrieve",
  "kind": "answer" | "refuse",
  "expected_support": ["evidence record ids a faithful answer should surface"],
  "expected_facts": ["substrings a correct answer must contain"]
}
```

The current six cases exercise both answer paths and all three refusal kinds:
cross-source composition (Müller), a retrieval lookup, the Lumière billing case
(whose document clause is a **known coverage miss** — it keeps coverage honestly
below 1.0), the Atlas mixed-currency refuse-to-sum, an ambiguous question, and an
out-of-scope question.

`expected_facts` and `expected_support` are checked against the answer the engine
actually produces. Faithfulness is gated (must be 1.0); coverage and quality are
reported as honest, improvable targets.
