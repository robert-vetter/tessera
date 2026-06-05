# Gold set

Curated, human-checked evaluation cases — one `*.json` file per case, each a
question with a known, fully-sourced correct answer. The eval harness
(`tessera.eval`) loads every `*.json` here.

**This directory is intentionally empty for now.** The curated cases and the
faithfulness / coverage / quality metrics that score them arrive in Unit 6 (see
[`specs/0011-eval-harness-scaffold.md`](../../specs/0011-eval-harness-scaffold.md)
and the roadmap). Until then `uv run tessera-eval` honestly reports
"no gold set evaluated yet" rather than a fabricated number.

Current minimal case shape (Unit 6 will extend it with expected-answer fields):

```json
{ "question": "..." }
```
