# DACH consultancy outreach — templates + process (send under the maintainer's identity)

*Drafted 2026-07-03. **The offer is the M18 pilot**
([docs/PILOT.md](../../docs/PILOT.md)): we instrument one of your agent use
cases with provenance + action receipts; you keep the audit artifact.
Target (ROADMAP2 / MARKET §5): 100–150 personalized messages, 3–4 touches →
≥5 calls → **≥2 design-partner pilots** with a written 2-week success
definition.*

Rules (MARKET.md): personalized beats volume; practitioner words (audit
trail, approval, receipts, blast radius) — never "trust layer" as the
headline, never "hallucination-free"; >50% of replies come from follow-ups,
so the sequence matters more than the first message; no attachments, one
link max per message.

**Privacy rule (spec 0124):** the committed `targets.example.csv` carries
company-level rows only (all already public in `docs/MARKET.md` §5).
Person-level research (names, contacts, dates) lives in `targets.csv`,
which is **gitignored** — it never enters the public repo.

## Personalization slots (fill per target, 2–3 min research each)

- `{name}` / `{company}` — the champion (Head of Data & AI / AI Practice
  Lead / BTP Practice Lead / Head of AI Engineering)
- `{hook}` — ONE specific, checkable observation: their public agent
  project, a Hack2Build/Joule-Studio mention, a talk, a blog post, a case
  study
- `{client_word}` — their language for clients ("Mandanten", "Kunden",
  "regulierte Kunden")

## Touch 1 — DE (LinkedIn DM or email, ≤120 words)

> Hallo {name},
>
> {hook} — deshalb schreibe ich Ihnen konkret.
>
> Wenn Sie Agenten für {client_word} bauen, kennen Sie die Frage nach dem
> Audit-Trail: *Woher stammt diese Antwort? Wer hat diese Aktion
> freigegeben?*
>
> Ich habe dafür eine Open-Source-Schicht gebaut: jede Aussage des Agenten
> ist auf die Quell-Datensätze rückführbar (und wird deterministisch
> gegengeprüft — kein LLM-Judge), was sich nicht belegen lässt, wird
> verweigert, und jede Aktion läuft über eine Freigabe und hinterlässt
> einen Receipt.
>
> Mein Angebot: ein **Pilot an einem Tag** — wir instrumentieren einen
> Ihrer Agent-Use-Cases, Sie behalten das Audit-Artefakt. On-prem,
> MIT-lizenziert, kein Vendor-Lock-in.
>
> 20 Minuten diese oder nächste Woche?
>
> {signature}

## Touch 1 — EN

> Hi {name},
>
> {hook} — which is exactly why I'm writing.
>
> If you're building agents for {client_word}, you know the audit
> question: *where did this answer come from, and who approved that
> action?*
>
> I've built an open-source layer for precisely that: every agent
> statement traces to its source records (re-checked deterministically —
> no LLM judge), anything unprovable is refused, and every action goes
> through an approval and leaves a receipt.
>
> The offer: a **pilot in a day** — we instrument one of your agent use
> cases; you keep the audit artifact. On-prem, MIT-licensed, no vendor
> lock-in.
>
> Worth 20 minutes this week or next?
>
> {signature}

## Touch 2 (+3–4 days): the demo

> Kurzer Nachtrag: die Live-Demo, klickbar in 3 Minuten —
> https://robert-vetter-tessera.hf.space — eine Antwort mit Beleg-Chips,
> eine ehrliche Verweigerung, und eine Aktion, die als Receipt endet.
> Falls das für {company} gerade kein Thema ist: an wen sollte ich mich
> wenden?

(EN mirror: "Quick follow-up: the live demo, clickable in 3 minutes … If
this isn't your topic right now — who at {company} should I ask?")

## Touch 3 (+1 week): the proof

> Ein Argument statt einer Behauptung: wir haben den Unterschied zwischen
> einem Agenten *mit* und *ohne* Evidenz-Gate gemessen — gleiches Korpus,
> gleiche Fragen, gleicher deterministischer Prüfer. Der ungegatete Agent
> beantwortet in der Mehrzahl der Fälle Fragen, die er verweigern müsste.
> Zahlen und Methode (offline reproduzierbar):
> https://github.com/robert-vetter/tessera/blob/main/docs/BENCHMARK.md
> Wenn Ihre {client_word} nach einem Audit-Trail fragen, ist das der
> Unterbau.

## Touch 4 (+2 weeks): the close-or-park

> Letzte Nachricht von mir dazu: Falls Interesse besteht, reserviere ich
> gern einen Pilot-Slot im {month} (Aufwand auf Ihrer Seite: ein Use-Case,
> ein Repo oder CSV-Verzeichnis, 2 Stunden eines Engineers). Falls nicht —
> danke fürs Lesen, und das Repo läuft nicht weg:
> github.com/robert-vetter/tessera

## Pilot success definition (agree in writing before starting — 2 weeks)

1. One named use case instrumented (their repo/CI or their CSV+docs
   corpus).
2. A grounded, provenance-complete answer set on their data; `smoke` (or
   the ingest analogue) clean, or its gaps named.
3. The audit artifact handed over (snapshot manifest, answers with claim
   trails, smoke report, receipts if the action flow was exercised).
4. A 30-minute debrief: what held, what refused, what's missing — and the
   explicit ask for a quotable sentence if they're happy.

## Call script skeleton (20 min)

- 0–3: their agent use cases, who the end client is, what the client
  audits.
- 3–8: demo, live (DEMO.md §2 beats 1–3 — answer w/ provenance, refusal,
  gated action → receipt).
- 8–12: the benchmark in one minute (why deterministic, what the floor
  means, what the gap column shows).
- 12–18: pilot scoping — pick the use case, name the success definition.
- 18–20: schedule the pilot day; who joins from their side.

## Tracking

Work the list in `targets.csv` (gitignored; person-level data stays
local; `targets.example.csv` has the columns + company-level seed rows
from the public MARKET.md list). Track touch dates, channel, reply, call,
pilot status, success-definition link. Review weekly; the metric that
matters is **pilots agreed**, not messages sent.
