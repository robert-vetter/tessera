# Demo & hosting — the live surface anyone can try

Tessera's substance is a terminal and an MCP server, but the *story* is visual:
a question, claims with per-claim verifier verdicts, a click-through to the
exact evidence, a principled refusal, and an action that ends in a receipt.
Milestone 17 packages that into a one-page web surface (`tessera-ui`, ADR 0027)
and this runbook to put it online.

Three things ship here: **how to run/host it**, the **3-minute demo script**,
and the **one-pager** copy.

---

## 1. Run it

Locally, key-free, in one command:

```bash
uv run tessera-ui                 # → http://127.0.0.1:8033
```

The page is stateless over the committed demo data, holds **no credential**,
and its action flow drives the **simulated** actuator only — it can neither
send anything nor leak anything (ADR 0027). Optional narration turns on only if
a key is present (`TESSERA_NARRATOR=anthropic`, ADR 0013); a hosted instance
runs without one.

### Host it (pick one; all have a usable free/hobby tier)

The image already carries the `tessera-ui` entry point. Bind to `0.0.0.0` and
expose the port; **set no secrets** — a public instance should be key-free by
design (no narration, no HANA, no GitHub token).

```bash
# From the repo's existing image (docs/ENGINEERING.md builds it):
docker build -t tessera .
docker run --rm -p 8033:8033 tessera tessera-ui --host 0.0.0.0 --port 8033
```

| Option | Shape | Notes |
|---|---|---|
| **Fly.io** | `fly launch` → `fly deploy` on the Dockerfile; `internal_port = 8033` | Smallest shared-cpu VM is ample; scale-to-zero keeps it free-ish. The honest default. |
| **Railway / Render** | point at the repo, start command `tessera-ui --host 0.0.0.0 --port $PORT` | Zero-config Docker or Nixpacks; free hobby tier. Read `$PORT` from the platform (pass `--port`). |
| **A small VM** (Hetzner/Fly Machine/EC2 micro) | run the `docker run` above behind a reverse proxy (Caddy for automatic TLS) | Most control; ~€4/month. Add the reverse proxy's rate limiting (the app has none — it is a demo). |

**Operational honesty for a public host:** the app builds an answer per request
(cheap, but not free) and ships no auth or rate limiting — it is a read-only
demonstrator (ADR 0027). Put a reverse-proxy rate limit in front of anything
public, and remember the compute is the only cost since there are no secrets to
protect. If you want the SAP-HANA online numbers or narration in a *private*
demo, set the keys there — never on the public instance.

---

## 2. The 3-minute demo (the script)

The arc is the industry's own post-Replit lesson (an agent deleted a production
database during a code freeze, then misreported the rollback — the canonical
"agents need evidence gates and receipts" story): **an agent should only say
what it can prove, and only do what you approve.** Tessera is that, live.

Open `tessera-ui`. Each beat is one URL, so the whole thing is clickable.

1. **The claim, proven (0:00–0:45).** Ask, in DevEx, *"Why did run R-1042
   fail?"* Point at the numbered claims, each with a green **✓ verifier-checked**
   chip. Open one claim's provenance: the exact log lines, the source file, the
   locator, the snapshot date. *"Every sentence traces to a record. The green
   chip isn't decoration — it's the eval's own verifier, run on this answer."*
2. **The refusal (0:45–1:15).** Ask *"Why did run R-1041 fail?"* — it passed.
   The page refuses: *"A principled refusal is the trust contract working: no
   evidence, no claim."* *"This is the part that would have stopped Replit — the
   system declines instead of confabulating."*
3. **The action, gated (1:15–2:15).** Back on R-1042, click **draft incident →**.
   Show the field table — every value verbatim, each with its own verdict, each
   traced. Click **preview the exact GitHub request →**: the real
   `POST /repos/{owner}/{repo}/issues` body, `sent: false`, every value grounded.
   Click **approve & execute (simulated)**: the receipt — `outcome: simulated`,
   `sent: false`. *"Nothing left the machine. The one real send Tessera ever did
   is on the record —"* open
   [`tessera-exec-oneshot#1`](https://github.com/robert-vetter/tessera-exec-oneshot/issues/1)
   *"— behind approval, with a committed receipt."*
4. **The measured floor (2:15–3:00).** Back to the home page's trust table.
   *"And it's measured: faithfulness is a hard 1.0 floor in CI — an unsupported
   claim fails the build. The sub-1.0 numbers are honest, kept-visible offline
   misses. Trust here is a number you can watch, not a vibe."* Close on the
   line: **"The agent can only say what it can prove — and only do what you
   approve."**

**Optional coda (for a technical audience):** show
[`data/agent_session/TRANSCRIPT.md`](https://github.com/robert-vetter/tessera/blob/main/data/agent_session/TRANSCRIPT.md) — a
real Claude agent doing exactly beats 1–3 through the MCP tools, unedited.

Recording tips: a screen capture at 1280×800, no cuts (every beat is a click),
narration read from the script above. Keep it under three minutes; the demo is
the argument.

---

## 3. The one-pager

**Tessera — the agent can only say what it can prove, and only do what you
approve.**

Enterprise AI fails less on fluency than on trust: agents mix sources, invent
plausible detail, and leave no way to check a claim — or to undo an action.
Tessera is an open, deterministic trust layer that fixes both ends.

- **Every claim is grounded.** Answers are built from a cross-source knowledge
  graph (ERP tables, contracts, CI logs, tickets) with **claim-level
  provenance** — each sentence traces to the exact records behind it. What
  can't be proven is **refused**, not guessed.
- **Every action leaves a receipt.** An agent drafts an action only when every
  field traces to a verifier-passing claim; the exact request is previewed, not
  sent; execution is behind approval and produces an auditable **receipt**. The
  agent may do only what you approve.
- **Trust is a number.** A built-in benchmark scores **faithfulness** with a
  CI-gated floor of 1.0 — no LLM judge, fully deterministic. Improvements are
  measured, not claimed.
- **On-prem by default.** No model vendor in the trust path; runs offline with
  zero runtime dependencies. Built toward SAP (HANA Cloud, MCP, Joule), portable
  everywhere.

*Open source (MIT). Live demo: `uv run tessera-ui`. MCP-native — plug it in as
your agents' evidence layer.* — github.com/robert-vetter/tessera

---

*(Deutsche Kurzfassung für DACH-Ansprache)*

**Tessera — der Agent darf nur sagen, was er beweisen kann, und nur tun, was Sie
freigeben.** Ein offener, deterministischer Trust-Layer für KI-Agenten: jede
Aussage ist auf die Quell-Datensätze zurückführbar (claim-level Provenance),
was sich nicht belegen lässt, wird **verweigert** statt geraten; jede Aktion
läuft über eine Freigabe und hinterlässt einen **auditierbaren Receipt**; und
die Treue zum Beleg ist als **Faithfulness-Score mit hartem CI-Grenzwert**
gemessen — kein LLM-Judge, kein Modell-Anbieter im Trust-Pfad, on-prem-fähig,
ausgerichtet auf SAP (HANA Cloud, MCP, Joule). *Open Source (MIT), MCP-nativ.*
