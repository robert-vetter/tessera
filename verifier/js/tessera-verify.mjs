#!/usr/bin/env node
// `tessera-verify` — the command-line front end (spec 0148, ADR 0038).
//
// All verification rules live in verify-core.mjs, which has zero imports and
// runs unchanged in a browser (docs/verify.html). This file adds only what a
// terminal needs: the filesystem, Ed25519 from node:crypto, rendering and
// exit codes.
//
// Usage:
//   node tessera-verify.mjs <bundle.tsb> [--approval a.json ...] [--json]

import { createHash, createPublicKey, verify as cryptoVerify } from "node:crypto";
import { readFileSync } from "node:fs";

import { parseRaw, setEd25519Verifier, verifyBundle } from "./verify-core.mjs";

const ED25519_SPKI_PREFIX = Buffer.from("302a300506032b6570032100", "hex");

setEd25519Verifier((publicKeyHex, message, signatureHex) => {
  const raw = Buffer.from(publicKeyHex, "hex");
  if (raw.length !== 32) return false;
  const key = createPublicKey({
    key: Buffer.concat([ED25519_SPKI_PREFIX, raw]),
    format: "der",
    type: "spki",
  });
  return cryptoVerify(null, Buffer.from(message), key, Buffer.from(signatureHex, "hex"));
});

/** The core's own SHA-256 is cross-checked against node:crypto here, so the
 *  hand-written hash can never drift unnoticed on the path that has a real
 *  one available (spec 0150 D2). */
export function nodeSha256(bytes) {
  return createHash("sha256").update(Buffer.from(bytes)).digest("hex");
}

// --- CLI --------------------------------------------------------------------------

const EXIT = { "PASS-PARTIAL": 0, "NOT-EVALUABLE": 3, FAIL: 2, TAMPERED: 4 };

function render(report, source) {
  const lines = [`bundle:    ${source} — independent verifier (JavaScript, zero deps)`];
  lines.push(`engine:    domain ${report.domain}`);
  lines.push(
    report.integrity_problems.length
      ? `integrity: BROKEN — ${report.integrity_problems.length} problem(s)`
      : "integrity: intact — every leaf and the root re-computed"
  );
  for (const problem of report.integrity_problems) lines.push(`  ! ${problem}`);
  if (report.signature) {
    lines.push(
      report.signature.status === "UNSIGNED"
        ? "signature: UNSIGNED"
        : report.signature.problems.length
          ? `signature: BROKEN — ${report.signature.problems.join("; ")}`
          : `signature: valid — key ${report.signature.key}`
    );
  }
  for (const approval of report.approvals) {
    lines.push(
      approval.valid
        ? `approval:  valid — key ${approval.approver}`
        : `approval:  INVALID — ${approval.problem}`
    );
  }
  for (const upstream of report.upstreams) {
    lines.push(`upstream:  ${upstream.root} → ${upstream.verdict}`);
  }
  if (report.withheld.length) {
    lines.push(
      `withheld:  ${report.withheld.length} item(s) — commitments intact, ` +
        "content not shared; claims citing them are not re-derivable here"
    );
  }
  const matched = report.claims.filter((c) => c.matches === true).length;
  lines.push(`claims:    ${matched}/${report.claims.length} re-executed and matched`);
  for (const problem of report.semantic_problems) lines.push(`  ! ${problem}`);
  lines.push("not done:  " + report.not_performed.join("; "));
  lines.push(`verdict:   ${report.verdict} (exit ${EXIT[report.verdict]})`);
  return lines.join("\n");
}

function main(argv) {
  const args = argv.slice(2);
  if (!args.length) {
    console.error("usage: tessera-verify.mjs <bundle.tsb> [--approval a.json ...] [--json]");
    return 64;
  }
  const asJson = args.includes("--json");
  const approvals = [];
  const positional = [];
  for (let i = 0; i < args.length; i += 1) {
    if (args[i] === "--approval") {
      approvals.push(parseRaw(readFileSync(args[i + 1], "utf8")).tree);
      i += 1;
    } else if (args[i] !== "--json") positional.push(args[i]);
  }
  const source = positional[0];
  let parsed;
  try {
    parsed = parseRaw(readFileSync(source, "utf8"));
  } catch (error) {
    console.error(`error: cannot read ${source}: ${error.message}`);
    return 4;
  }
  if (!parsed.sawSource) {
    // Without source-text access a number's lexical form is unrecoverable, so
    // the canonical bytes — and therefore every digest — cannot be reproduced.
    // Refusing is the only honest option; guessing would produce false
    // TAMPERED verdicts.
    console.error(
      "error: this runtime does not expose JSON source text (Node >= 21 " +
        "required). Canonical bytes cannot be reproduced without it; use the " +
        "reference verifier instead of trusting a guess."
    );
    return 4;
  }
  const report = verifyBundle(parsed.tree, approvals);
  console.log(asJson ? JSON.stringify(report, null, 2) : render(report, source));
  return EXIT[report.verdict];
}

process.exitCode = main(process.argv);
