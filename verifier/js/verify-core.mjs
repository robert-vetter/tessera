// The Tessera trust-bundle verifier — portable core (spec 0148/0150, ADR 0038/0040).
//
// ZERO IMPORTS on purpose: this exact file runs in Node (behind the CLI in
// tessera-verify.mjs) and in a browser (inlined into docs/verify.html). One
// implementation, two front ends — a page that re-implemented these rules
// would be a third thing to keep correct and would prove nothing about the
// format.
//
// Written from the format contract (ADR 0031 format, 0032 signing, 0033
// chains, 0035 approvals, 0039 redaction), not translated from the Python
// reference — that independence is what makes agreement between the two mean
// something.
//
// HONEST SCOPE: two checks need the engine itself and are not portable —
// answer re-derivation (re-running the domain router) and action
// re-derivation (re-running the drafting pipeline). So this verifier can
// never report a full PASS; its ceiling is PASS-PARTIAL and every report
// prints what it did not do.

// --- SHA-256, dependency-free ----------------------------------------------------
//
// Node's crypto is unavailable in a browser and WebCrypto's digest is async,
// which would make every function in this file async. A compact SHA-256 keeps
// the verifier synchronous and identical in both environments. It is
// differentially tested against node:crypto (spec 0150), so it cannot drift.

const K = [
  0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1,
  0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
  0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786,
  0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
  0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147,
  0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
  0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b,
  0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
  0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a,
  0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
  0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
];

const rotr = (x, n) => (x >>> n) | (x << (32 - n));

/** SHA-256 over UTF-8 bytes, returned as lowercase hex. */
export function sha256(bytes) {
  const length = bytes.length;
  const withPadding = new Uint8Array((((length + 8) >> 6) + 1) << 6);
  withPadding.set(bytes);
  withPadding[length] = 0x80;
  const bitLength = length * 8;
  const view = new DataView(withPadding.buffer);
  view.setUint32(withPadding.length - 4, bitLength >>> 0, false);
  view.setUint32(withPadding.length - 8, Math.floor(bitLength / 0x100000000), false);

  const h = [
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
    0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
  ];
  const w = new Uint32Array(64);
  for (let offset = 0; offset < withPadding.length; offset += 64) {
    for (let i = 0; i < 16; i += 1) w[i] = view.getUint32(offset + i * 4, false);
    for (let i = 16; i < 64; i += 1) {
      const s0 = rotr(w[i - 15], 7) ^ rotr(w[i - 15], 18) ^ (w[i - 15] >>> 3);
      const s1 = rotr(w[i - 2], 17) ^ rotr(w[i - 2], 19) ^ (w[i - 2] >>> 10);
      w[i] = (w[i - 16] + s0 + w[i - 7] + s1) >>> 0;
    }
    let [a, b, c, d, e, f, g, hh] = h;
    for (let i = 0; i < 64; i += 1) {
      const S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
      const ch = (e & f) ^ (~e & g);
      const t1 = (hh + S1 + ch + K[i] + w[i]) >>> 0;
      const S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
      const maj = (a & b) ^ (a & c) ^ (b & c);
      const t2 = (S0 + maj) >>> 0;
      hh = g; g = f; f = e; e = (d + t1) >>> 0;
      d = c; c = b; b = a; a = (t1 + t2) >>> 0;
    }
    h[0] = (h[0] + a) >>> 0; h[1] = (h[1] + b) >>> 0;
    h[2] = (h[2] + c) >>> 0; h[3] = (h[3] + d) >>> 0;
    h[4] = (h[4] + e) >>> 0; h[5] = (h[5] + f) >>> 0;
    h[6] = (h[6] + g) >>> 0; h[7] = (h[7] + hh) >>> 0;
  }
  return h.map((x) => x.toString(16).padStart(8, "0")).join("");
}

const UTF8 = new TextEncoder();

// --- canonical bytes (tessera-canonical-json-1) ----------------------------------
//
// json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).
// Key order is by code unit, which matches Python's sort over str for the
// ASCII keys this format uses.
//
// NUMBERS — a portability finding this implementation produced (spec 0148).
// The producer is Python, where 1.0 (float) serialises as "1.0" and 1 (int)
// as "1". A language without that type distinction cannot reproduce the
// canonical bytes from a *parsed* document: JSON.parse turns both into the
// same Number, and re-emitting gives "1". Confidence scores in the
// resolution/mention sections are exactly such floats, so this is not
// theoretical — it changes two leaf digests and therefore the root.
//
// The fix that keeps the format honest for any implementation: canonical
// bytes preserve the *lexical form* a number was parsed from. Node exposes
// it via the JSON.parse reviver's `context.source` (Node >= 21); numbers are
// wrapped in RawNumber and emitted verbatim. The rule is now stated in
// docs/BUNDLE.md and ADR 0031 — an independent implementation is also a
// specification review.

class RawNumber {
  constructor(raw) {
    this.raw = raw;
  }
  valueOf() {
    return Number(this.raw);
  }
}

/** Parse preserving each number's source text (for hashing). */
export function parseRaw(text) {
  let sawSource = false;
  const tree = JSON.parse(text, function (key, value, context) {
    if (typeof value === "number") {
      const source = context?.source;
      if (source === undefined) return value;
      sawSource = true;
      return new RawNumber(source);
    }
    return value;
  });
  return { tree, sawSource };
}

/** The same document with numbers as ordinary Numbers (for logic). */
export function plain(value) {
  if (value instanceof RawNumber) return value.valueOf();
  if (Array.isArray(value)) return value.map(plain);
  if (value && typeof value === "object") {
    const out = {};
    for (const [key, item] of Object.entries(value)) out[key] = plain(item);
    return out;
  }
  return value;
}

export function canonical(value) {
  if (value instanceof RawNumber) return value.raw;
  if (value === null || typeof value === "boolean") return JSON.stringify(value);
  if (typeof value === "number") return JSON.stringify(value);
  if (typeof value === "string") return JSON.stringify(value);
  if (Array.isArray(value)) return "[" + value.map(canonical).join(",") + "]";
  const keys = Object.keys(value).sort();
  return (
    "{" + keys.map((k) => JSON.stringify(k) + ":" + canonical(value[k])).join(",") + "}"
  );
}

function sha256Hex(bytes) {
  return "sha256:" + sha256(bytes);
}

export function digest(value) {
  return sha256Hex(UTF8.encode(canonical(value)));
}

// --- the format contract ---------------------------------------------------------

const FORMAT_NAME = "tessera-trust-bundle";
const FORMAT_MAJOR = 1;
const CLOSURE_FULL = "full-graph-snapshot";
const CLOSURE_CHAIN = "chain-snapshot";
const CANONICALIZATION = "tessera-canonical-json-1";

const TOP_LEVEL_KEYS = new Set([
  "format", "engine", "result", "evidence_closure",
  "integrity", "action", "signature", "anchor",
]);
const CLOSURE_KEYS = new Set(["kind", "graph", "kb"]);
const CHAIN_CLOSURE_KEYS = new Set(["kind", "graph", "kb", "upstream"]);
const GRAPH_KEYS = new Set(["nodes", "edges", "resolutions", "mentions"]);

/** Redaction (spec 0149): withheld content keeps only the commitment the
 *  bundle was sealed with, which is what preserves the root. Safe because
 *  withheld content is unverifiable — a redacted bundle proves LESS, never
 *  more — and a wrong commitment moves the root and breaks any signature. */
function isWithheld(value) {
  return Boolean(value) && typeof value === "object" && plain(value.redacted) === true;
}

function leafOf(value, name, committed) {
  if (isWithheld(value)) {
    if (!committed || !(name in committed)) {
      throw new Error(`withheld leaf '${name}' has no commitment in the manifest`);
    }
    return committed[name];
  }
  return digest(value);
}

export function leafManifest(bundle, committed) {
  const closure = bundle.evidence_closure;
  const graph = closure.graph;
  const leaves = {
    format: digest(bundle.format),
    engine: digest(bundle.engine),
    result: leafOf(bundle.result, "result", committed),
    action: digest(bundle.action ?? null),
    "closure.kind": digest(closure.kind),
    kb: leafOf(closure.kb, "kb", committed),
    "graph.edges": leafOf(graph.edges, "graph.edges", committed),
    "graph.resolutions": leafOf(graph.resolutions, "graph.resolutions", committed),
    "graph.mentions": leafOf(graph.mentions, "graph.mentions", committed),
  };
  for (const node of graph.nodes) {
    const leaf = "node:" + node.record.id;
    if (leaf in leaves) throw new Error(`duplicate node id ${node.record.id}`);
    leaves[leaf] = leafOf(node, leaf, committed);
  }
  if (closure.kind === CLOSURE_CHAIN) {
    for (const upstream of closure.upstream ?? []) {
      const leaf = "upstream:" + upstream.integrity.root;
      if (leaf in leaves) throw new Error(`duplicate upstream ${upstream.integrity.root}`);
      leaves[leaf] = digest(upstream);
    }
  }
  return leaves;
}

function sectionSetProblems(bundle) {
  const problems = [];
  for (const key of Object.keys(bundle)) {
    if (!TOP_LEVEL_KEYS.has(key)) problems.push(`unexpected top-level section '${key}'`);
  }
  const closure = bundle.evidence_closure;
  const allowed = closure?.kind === CLOSURE_CHAIN ? CHAIN_CLOSURE_KEYS : CLOSURE_KEYS;
  for (const key of Object.keys(closure ?? {})) {
    if (!allowed.has(key)) problems.push(`unexpected evidence_closure key '${key}'`);
  }
  for (const key of Object.keys(closure?.graph ?? {})) {
    if (!GRAPH_KEYS.has(key)) problems.push(`unexpected graph key '${key}'`);
  }
  return problems;
}

function integrityProblems(bundle) {
  const problems = [];
  const integrity = bundle.integrity;
  if (!integrity || typeof integrity !== "object") return ["missing integrity section"];
  if (integrity.canonicalization !== CANONICALIZATION) {
    return [`canonicalization '${integrity.canonicalization}' is not ${CANONICALIZATION}`];
  }
  problems.push(...sectionSetProblems(bundle));
  const stored = plain(integrity.leaves ?? {});
  const recomputed = leafManifest(bundle, stored);
  for (const name of Object.keys(recomputed).sort()) {
    if (!(name in stored)) problems.push(`missing leaf '${name}'`);
  }
  for (const name of Object.keys(stored).sort()) {
    if (!(name in recomputed)) problems.push(`unexpected leaf '${name}'`);
  }
  for (const name of Object.keys(recomputed).sort()) {
    if (name in stored && stored[name] !== recomputed[name]) {
      problems.push(`leaf '${name}' does not match its content`);
    }
  }
  if (plain(integrity.root) !== digest(recomputed)) {
    problems.push("root does not recompute from the content");
  }
  return problems;
}

// --- signature (Ed25519 over integrity.root) -------------------------------------

// Ed25519 is supplied by the host (spec 0150 D3): the CLI passes node:crypto,
// a browser build passes nothing and the report SAYS the signature was not
// checked rather than implying it was. Never a silent gap.
let ed25519Verifier = null;

/** Install the host's Ed25519 verification, or leave it unset. */
export function setEd25519Verifier(fn) {
  ed25519Verifier = fn;
}

function verifyEd25519(publicKeyHex, message, signatureHex) {
  if (!ed25519Verifier) return null; // "cannot check here", not "invalid"
  return ed25519Verifier(publicKeyHex, message, signatureHex);
}

function signatureProblems(bundle) {
  const signature = bundle.signature;
  if (signature === null || signature === undefined) return { status: "UNSIGNED", problems: [], key: null };
  if (signature.algorithm !== "ed25519") {
    return { status: "SIGNED", problems: [`unsupported algorithm '${signature.algorithm}'`], key: null };
  }
  const root = bundle.integrity?.root;
  if (typeof root !== "string") {
    return { status: "SIGNED", problems: ["no sealed root to verify against"], key: signature.public_key };
  }
  const ok = verifyEd25519(signature.public_key, UTF8.encode(root), signature.signature);
  if (ok === null) {
    return {
      status: "SIGNED",
      problems: [],
      key: signature.public_key,
      unchecked: "signature verification is not available in this build",
    };
  }
  return {
    status: "SIGNED",
    problems: ok ? [] : ["the signature does not verify against the sealed root"],
    key: signature.public_key,
  };
}

// --- detached approvals (ADR 0035) -----------------------------------------------

function checkApproval(rawArtifact, recomputedRoot) {
  // Logic reads the plain tree; the signed payload is canonicalised from the
  // source-preserving one, so a future approval carrying a float still hashes
  // identically to the producer's bytes.
  const artifact = plain(rawArtifact);
  if (artifact?.format?.name !== "tessera-approval") {
    return { valid: false, problem: "not an approval artifact", approver: "?" };
  }
  if (artifact.format.major !== 1) {
    return { valid: false, problem: `unsupported approval major ${artifact.format.major}`, approver: "?" };
  }
  const approver = artifact.approver?.public_key ?? "?";
  if (artifact.approves_root !== recomputedRoot) {
    return {
      valid: false,
      approver,
      problem: `approves a different bundle (${artifact.approves_root}) than this one (${recomputedRoot})`,
    };
  }
  const payload = {
    format: rawArtifact.format,
    approves_root: rawArtifact.approves_root,
    note: rawArtifact.note ?? null,
    at: rawArtifact.at ?? null,
  };
  const ok = verifyEd25519(approver, UTF8.encode(canonical(payload)), artifact.signature);
  if (ok === null) {
    return {
      valid: false,
      approver,
      problem: "approval signatures cannot be checked in this build",
    };
  }
  return { valid: ok, approver, problem: ok ? null : "the approval signature does not verify" };
}

// --- name normalisation (must match the reference exactly) -----------------------

function normalize(text) {
  const folded = text
    .toLowerCase()
    .replaceAll("ä", "ae")
    .replaceAll("ö", "oe")
    .replaceAll("ü", "ue")
    .replaceAll("ß", "ss");
  return folded
    .normalize("NFKD")
    .replace(/\p{M}/gu, "")
    .replace(/[^a-z0-9]/g, "");
}

// --- money as integer cents (never floats) ---------------------------------------

function cents(raw) {
  const cleaned = raw.replaceAll(",", "");
  const match = /^(\d+)\.(\d{2})$/.exec(cleaned);
  if (!match) return null;
  return BigInt(match[1]) * 100n + BigInt(match[2]);
}

// --- the graph, reconstructed ----------------------------------------------------

function buildGraph(closure) {
  const nodes = new Map();
  for (const node of closure.graph.nodes ?? []) {
    if (isWithheld(node)) continue; // committed, not shared
    nodes.set(node.record.id, node);
  }
  return {
    nodes,
    edges: closure.graph.edges,
    resolutions: closure.graph.resolutions,
    attr: (id, key) => {
      const node = nodes.get(id);
      if (!node) return null;
      for (const [k, v] of node.attributes ?? []) if (k === key) return v;
      return null;
    },
  };
}

/** Connected components over resolution assertions — entities are derived,
 *  never stored (ADR 0004). */
function entityOf(graph, id) {
  const adjacency = new Map();
  for (const res of graph.resolutions) {
    if (!adjacency.has(res.node_a)) adjacency.set(res.node_a, new Set());
    if (!adjacency.has(res.node_b)) adjacency.set(res.node_b, new Set());
    adjacency.get(res.node_a).add(res.node_b);
    adjacency.get(res.node_b).add(res.node_a);
  }
  const seen = new Set([id]);
  const stack = [id];
  while (stack.length) {
    const current = stack.pop();
    for (const next of adjacency.get(current) ?? []) {
      if (!seen.has(next)) {
        seen.add(next);
        stack.push(next);
      }
    }
  }
  return seen;
}

function clusters(graph) {
  const out = [];
  const assigned = new Set();
  for (const id of graph.nodes.keys()) {
    if (assigned.has(id)) continue;
    const component = entityOf(graph, id);
    for (const member of component) assigned.add(member);
    out.push(component);
  }
  return out;
}

function clusterNames(graph, cluster) {
  const names = new Set();
  for (const id of cluster) {
    const node = graph.nodes.get(id);
    if (node?.name) names.add(normalize(node.name));
  }
  return names;
}

function entityOfRow(graph, rowId) {
  for (const edge of graph.edges) {
    if (edge.src === rowId && edge.relation === "sold_to") return entityOf(graph, edge.dst);
  }
  return null;
}

function rowsSoldTo(graph, cluster) {
  const ids = new Set();
  for (const edge of graph.edges) {
    if (edge.relation === "sold_to" && cluster.has(edge.dst)) ids.add(edge.src);
  }
  return ids;
}

// --- claim grammars --------------------------------------------------------------
//
// Tri-state, exactly as the reference: true/false is an owned verdict, null
// means "this grammar does not speak for this claim" and the next one is
// consulted. Precedence: the vertical's declared shapes in order, then the
// generic shared-fragment grammar, then verbatim containment.

const MONEY = /\b([A-Z]{3}) ([\d,]+\.\d{2})\b/;
const COUNTS = /spanning (\d+) customer record\(s\) and (\d+) address record\(s\)/;
const REFUSE = /Refused to sum across (\w+) and (\w+)/;
const COMPARE =
  /'(.+?)' \(([A-Z]{3}) ([\d,]+\.\d{2}) across (\d+) order\(s\)\) exceeds '(.+?)' \(([A-Z]{3}) ([\d,]+\.\d{2}) across (\d+) order\(s\)\) in total net order value/;
const SUPERLATIVE =
  /Among (\d+) entities with ([A-Z]{3}) orders, '(.+?)' has the highest total net order value: ([A-Z]{3}) ([\d,]+\.\d{2})/;
const SHARED_FRAGMENT = /"([^"]+)" appears in ([^"]+)$/;
const NAMED_SOURCES = /'([^']+)'/g;

function compareConclusion(claim, graph) {
  const match = COMPARE.exec(claim.text);
  if (!match || !graph) return null;
  const sides = [
    [match[1], match[2], match[3], match[4]],
    [match[5], match[6], match[7], match[8]],
  ];
  const totals = [];
  for (const [name, currency, raw, count] of sides) {
    const stated = cents(raw);
    if (stated === null) return false;
    const wanted = normalize(name);
    const rows = [];
    for (const evidence of claim.support) {
      const entity = entityOfRow(graph, evidence.id);
      if (entity && clusterNames(graph, entity).has(wanted)) rows.push(evidence.id);
    }
    if (rows.length !== Number(count)) return false;
    if (rows.some((id) => graph.attr(id, "currency") !== currency)) return false;
    let total = 0n;
    for (const id of rows) total += cents(graph.attr(id, "net_amount") ?? "0.00") ?? 0n;
    if (total !== stated) return false;
    totals.push(total);
  }
  return totals[0] > totals[1];
}

function superlativeConclusion(claim, graph) {
  const match = SUPERLATIVE.exec(claim.text);
  if (!match || !graph) return null;
  const statedCount = Number(match[1]);
  const currency = match[2];
  const winner = normalize(match[3]);
  if (match[4] !== currency) return false;
  const stated = cents(match[5]);
  if (stated === null) return false;

  const ranked = [];
  for (const cluster of clusters(graph)) {
    if (clusterNames(graph, cluster).size === 0) continue;
    const rows = [...rowsSoldTo(graph, cluster)].filter(
      (id) => graph.attr(id, "currency") === currency
    );
    if (!rows.length) continue;
    let total = 0n;
    for (const id of rows) total += cents(graph.attr(id, "net_amount") ?? "0.00") ?? 0n;
    ranked.push([total, cluster]);
  }
  if (ranked.length !== statedCount || !ranked.length) return false;
  let best = ranked[0];
  for (const entry of ranked) if (entry[0] > best[0]) best = entry;
  if (best[0] !== stated || !clusterNames(graph, best[1]).has(winner)) return false;
  let citedTotal = 0n;
  for (const evidence of claim.support) {
    citedTotal += cents(graph.attr(evidence.id, "net_amount") ?? "0.00") ?? 0n;
  }
  return (
    citedTotal === stated &&
    claim.support.every((e) => graph.attr(e.id, "currency") === currency)
  );
}

function conflictDisclosure(claim) {
  // Needs engine-side document parsing (renewal_date_of): not portable.
  if (!claim.text.includes("disagree on the renewal date")) return null;
  return "NOT-EVALUABLE";
}

function aggregateRecompute(claim, graph) {
  const money = MONEY.exec(claim.text);
  if (!money || !claim.text.toLowerCase().includes("net order value")) return null;
  const stated = cents(money[2]);
  if (stated === null) return false;
  const cited = claim.support.map((e) => e.id);
  if (!cited.length) return null;
  if (!cited.every((id) => graph.nodes.has(id) && graph.attr(id, "currency") === money[1])) {
    return null;
  }
  let total = 0n;
  for (const id of cited) total += cents(graph.attr(id, "net_amount") ?? "0.00") ?? 0n;
  return total === stated ? true : null;
}

function countMatch(claim, graph) {
  const counts = COUNTS.exec(claim.text);
  if (!counts) return null;
  const kinds = claim.support
    .filter((e) => graph.nodes.has(e.id))
    .map((e) => graph.nodes.get(e.id).kind);
  const customers = kinds.filter((k) => k === "I_Customer").length;
  const addresses = kinds.filter((k) => k === "I_AddrOrgNamePostalAddress").length;
  return customers === Number(counts[1]) && addresses === Number(counts[2]) ? true : null;
}

function refuseToSum(claim, graph) {
  const refuse = REFUSE.exec(claim.text);
  if (!refuse) return null;
  const named = new Set([refuse[1], refuse[2]]);
  const cited = new Set();
  for (const evidence of claim.support) {
    const currency = graph.attr(evidence.id, "currency");
    if (currency) cited.add(currency);
  }
  return [...named].every((c) => cited.has(c)) ? true : null;
}

function chainCitation(claim) {
  if (claim.support.length !== 1) return null;
  if (claim.support[0].locator?.kind !== "bundle-claim") return null;
  return claim.text === claim.support[0].text;
}

const VERTICAL_SHAPES = {
  "tessera.business.claims.compare_conclusion": compareConclusion,
  "tessera.business.claims.superlative_conclusion": superlativeConclusion,
  "tessera.business.claims.conflict_disclosure": (claim) => conflictDisclosure(claim),
  "tessera.business.claims.aggregate_recompute": aggregateRecompute,
  "tessera.business.claims.count_match": countMatch,
  "tessera.business.claims.refuse_to_sum": refuseToSum,
  "tessera.bundle.chain.chain_citation": (claim) => chainCitation(claim),
};

/** The generic grammars, in the reference's order: shared fragment (owns its
 *  verdict), then verbatim containment. */
function genericVerdict(claim) {
  const shared = SHARED_FRAGMENT.exec(claim.text);
  if (shared) {
    const fragment = shared[1];
    const named = new Set([...shared[2].matchAll(NAMED_SOURCES)].map((m) => m[1]));
    if (claim.support.length < 2 || named.size < 2) return false;
    const sources = new Set(claim.support.map((e) => e.source));
    if (named.size !== sources.size || [...named].some((n) => !sources.has(n))) return false;
    const needle = normalize(fragment);
    return Boolean(needle) && claim.support.every((e) => normalize(e.text).includes(needle));
  }
  const needle = normalize(claim.text);
  return Boolean(needle) && claim.support.some((e) => normalize(e.text).includes(needle));
}

function claimVerdict(claim, graph, declaredShapes) {
  for (const identifier of declaredShapes) {
    const shape = VERTICAL_SHAPES[identifier];
    if (!shape) return "NOT-EVALUABLE"; // an unknown grammar: never guess
    const verdict = shape(claim, graph);
    if (verdict === "NOT-EVALUABLE") return "NOT-EVALUABLE";
    if (verdict !== null) return verdict;
  }
  return genericVerdict(claim);
}

// --- the verifier ----------------------------------------------------------------

export function verifyBundle(rawBundle, approvals = []) {
  // Hashing reads the source-preserving tree; all logic reads the plain one.
  const bundle = plain(rawBundle);
  const report = {
    verdict: null,
    domain: bundle?.engine?.domain ?? null,
    integrity_problems: [],
    signature: null,
    semantic_problems: [],
    claims: [],
    approvals: [],
    upstreams: [],
    withheld: [],
    not_performed: [
      "answer re-derivation (needs the engine's router)",
      "action re-derivation (needs the engine's drafting pipeline)",
    ],
  };

  if (bundle?.format?.name !== FORMAT_NAME) {
    report.verdict = "TAMPERED";
    report.integrity_problems.push(`not a trust bundle: format.name is ${bundle?.format?.name}`);
    return report;
  }
  if (bundle.format.major !== FORMAT_MAJOR) {
    report.verdict = "TAMPERED";
    report.integrity_problems.push(`unsupported format major ${bundle.format.major}`);
    return report;
  }
  if (bundle.anchor !== null && bundle.anchor !== undefined) {
    report.verdict = "TAMPERED";
    report.integrity_problems.push("the anchor section is reserved and not verifiable");
    return report;
  }

  try {
    report.integrity_problems = integrityProblems(rawBundle);
  } catch (error) {
    report.verdict = "TAMPERED";
    report.integrity_problems = [String(error.message ?? error)];
    return report;
  }
  const signature = signatureProblems(bundle);
  report.signature = signature;
  if (report.integrity_problems.length || signature.problems.length) {
    report.verdict = "TAMPERED";
    return report;
  }

  const recomputedRoot = digest(
    leafManifest(rawBundle, plain(rawBundle.integrity?.leaves ?? {}))
  );
  for (const artifact of approvals) {
    report.approvals.push(checkApproval(artifact, recomputedRoot));
  }

  const closure = bundle.evidence_closure;
  const expectedKind = report.domain === "chain" ? CLOSURE_CHAIN : CLOSURE_FULL;
  if (closure.kind !== expectedKind) {
    report.semantic_problems.push(
      `closure kind '${closure.kind}' does not match the sealed domain (expected '${expectedKind}')`
    );
  }

  const graph = buildGraph(closure);
  const result = bundle.result;

  // Referential integrity: every cited id must resolve to a packaged node.
  for (const claim of result.claims ?? []) {
    for (const evidence of claim.support ?? []) {
      const withheldHere = (closure.graph?.nodes ?? []).some(
        (node) => isWithheld(node) && node.record?.id === evidence.id
      );
      if (!graph.nodes.has(evidence.id) && !withheldHere) {
        report.semantic_problems.push(`cited record '${evidence.id}' is absent from the graph`);
      }
    }
  }

  // Chain: recursively verify every embedded upstream, then bind the derived
  // records to the upstream claims they quote.
  if (closure.kind === CLOSURE_CHAIN) {
    const passing = new Map();
    // Recurse on the RAW upstreams: each needs its own integrity recompute.
    for (const upstream of rawBundle.evidence_closure.upstream ?? []) {
      const sub = verifyBundle(upstream);
      report.upstreams.push({ root: upstream.integrity?.root ?? "?", verdict: sub.verdict });
      if (sub.verdict === "PASS-PARTIAL") passing.set(upstream.integrity.root, { upstream, sub });
      else {
        report.semantic_problems.push(
          `embedded upstream ${upstream.integrity?.root} does not re-verify (${sub.verdict})`
        );
      }
    }
    for (const record of closure.kb.records ?? []) {
      const parts = Object.fromEntries(record.origin.locator.parts ?? []);
      const cited = passing.get(parts.bundle);
      if (record.origin.locator.kind !== "bundle-claim" || !parts.bundle) {
        report.semantic_problems.push(`chain record '${record.id}' does not cite an upstream claim`);
        continue;
      }
      if (!cited) {
        report.semantic_problems.push(
          `chain record '${record.id}' cites ${parts.bundle}, which is not embedded-and-passing`
        );
        continue;
      }
      const index = Number(parts.claim);
      const upstreamClaim = cited.upstream.result.claims?.[index];
      if (!upstreamClaim || upstreamClaim.text !== record.text) {
        report.semantic_problems.push(
          `chain record '${record.id}' does not match upstream claim ${index} — the cited text was altered`
        );
      }
    }
  }

  // Claim-level semantic re-execution.
  const declared = bundle.engine.claim_shapes ?? [];
  const withheldIds = new Set(
    (closure.graph?.nodes ?? [])
      .filter((node) => isWithheld(node))
      .map((node) => node.record?.id)
  );
  const withheldSections = ["kb", "graph", "result"].filter((name) =>
    isWithheld(name === "result" ? bundle.result : closure[name])
  );
  report.withheld = [...withheldIds, ...withheldSections];
  let notEvaluable = 0;
  for (const [index, claim] of (result.claims ?? []).entries()) {
    if ((claim.support ?? []).some((e) => withheldIds.has(e.id))) {
      // Withheld, not wrong: reported, never counted as verified.
      report.claims.push({ index, rederived: false, recorded: claim.verified, matches: null });
      continue;
    }
    const rederived = claimVerdict(claim, graph, declared);
    if (rederived === "NOT-EVALUABLE") {
      notEvaluable += 1;
      report.claims.push({ index, rederived: null, recorded: claim.verified, matches: null });
      continue;
    }
    const matches = rederived === claim.verified;
    report.claims.push({ index, rederived, recorded: claim.verified, matches });
    if (!matches) {
      report.semantic_problems.push(
        `claim ${index}: recorded verified=${claim.verified} but re-execution says ${rederived}`
      );
    } else if (!rederived) {
      report.semantic_problems.push(`claim ${index}: honestly unverified (degraded)`);
    }
  }

  if (report.semantic_problems.length) report.verdict = "FAIL";
  else if (notEvaluable || report.withheld.length) report.verdict = "NOT-EVALUABLE";
  else report.verdict = "PASS-PARTIAL";
  return report;
}
