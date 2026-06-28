#!/usr/bin/env python3
"""Generate the synthetic, SALT-shaped business dataset under data/salt_synthetic/.

This is a **dev-time** generator, not part of the runtime. It produces a small,
deterministic dataset that uses SAP SALT's *real* table/column/join structure
(see docs/adr and specs/0010) but contains **no real SALT data** — SALT itself is
access-gated and is not redistributed here. Because we generate against SALT's
actual schema, ingesting the real SALT dataset later is a drop-in swap.

Two properties matter and are tested downstream:

- **Deterministic.** A fixed seed makes the output byte-for-byte reproducible, so
  the repo stays clone-and-run and the eval is reproducible. Anchor entities are
  chosen deterministically too, not just the surrounding rows.
- **Genuine entity-resolution difficulty.** The same real-world organization
  appears under varying forms — legal-form suffix variants (GmbH/Gmbh/G.m.b.H),
  abbreviations, umlaut folding, typos, and differing address formats — across
  the customer master, the address master, and as duplicate customers. This is
  so Unit 4's entity resolution faces a real problem, not a planted-easy one.

Each customer master row also carries a ``VATRegistration`` column (Milestone 10,
spec 0078) — the exact legal-entity identity key that separates two genuinely
distinct firms even when their name **and** address coincide (the residual that
name + address ER, Milestone 9, cannot reach). It is assigned **per canonical
entity** (every duplicate record of one firm shares it; distinct firms differ), so
multi-field ER decides on it without splitting a genuine merge. The value is a
country-prefixed exact key (``<CC><9 digits>``); for the German demonstration firms
this is the real EU VAT shape (``DE`` + 9 digits). Non-EU firms would in reality
carry a national tax id rather than an EU VAT — the synthetic generator populates a
uniform country-prefixed key for every customer (so the column is realistically
non-empty), and the entity-resolution mechanism relies only on **exact equality**,
so the synthetic format is a faithful-enough stand-in.

Run with:  ``uv run python scripts/generate_salt_synthetic.py``
Pure stdlib — no third-party dependency.
"""

from __future__ import annotations

import csv
import json
import random
import zlib
from pathlib import Path


def _stable_hash(text: str) -> int:
    """Process-independent hash. ``hash()`` is randomized per run, which would
    break the byte-for-byte reproducibility this generator promises."""
    return zlib.crc32(text.encode("utf-8"))


# Deterministic knobs. SNAPSHOT_DATE is the dataset's honest "as of" date and
# becomes every ingested record's ingestion timestamp (see sources/salt.py), so
# provenance metadata stays deterministic rather than wall-clock.
SEED = 20260605
SNAPSHOT_DATE = "2026-06-05"
TARGET_CUSTOMERS = 40

OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "salt_synthetic"


# --- Real-world "true entities" the synthetic records are noisy views of -------
# (canonical_name, street, house_no, postal, city, country)
_ENTITIES: tuple[tuple[str, str, str, str, str, str], ...] = (
    ("Nordwind Logistik GmbH", "Industriestrasse", "12", "20095", "Hamburg", "DE"),
    ("Bayerische Stahlwerke AG", "Hauptstrasse", "5", "80331", "München", "DE"),
    ("Rheintal Pharma GmbH", "Am Rheinufer", "44", "50667", "Köln", "DE"),
    ("Schäfer Präzisionstechnik GmbH", "Werkstrasse", "8", "70173", "Stuttgart", "DE"),
    ("Alpenblick Touristik AG", "Bergstrasse", "21", "6020", "Innsbruck", "AT"),
    ("Helvetia Finanz AG", "Bahnhofstrasse", "3", "8001", "Zürich", "CH"),
    ("Acme International Inc", "Market Street", "200", "94105", "San Francisco", "US"),
    ("Globex Technologies Inc", "Innovation Way", "17", "02142", "Cambridge", "US"),
    ("Initech Solutions LLC", "Commerce Blvd", "900", "78701", "Austin", "US"),
    ("Umbrella Health Corp", "Wellness Ave", "55", "10018", "New York", "US"),
    ("Meridian Shipping Ltd", "Dockside Road", "7", "EC3R 6AF", "London", "GB"),
    ("Albion Foods Ltd", "Market Square", "13", "M1 1AE", "Manchester", "GB"),
    ("Lumière Énergie SARL", "Rue de la Paix", "9", "75002", "Paris", "FR"),
    ("Provence Vins SA", "Avenue du Soleil", "30", "13001", "Marseille", "FR"),
    ("Nordic Timber AS", "Havnegata", "4", "0150", "Oslo", "NO"),
    ("Vega Robotics GmbH", "Technologiepark", "2", "01069", "Dresden", "DE"),
    ("Orion Datentechnik GmbH", "Forschungsallee", "19", "12489", "Berlin", "DE"),
    ("Castor & Pollux Handels OHG", "Marktplatz", "1", "04109", "Leipzig", "DE"),
    ("Tiber Costruzioni SpA", "Via Roma", "88", "00184", "Roma", "IT"),
    ("Adriatica Marittima SpA", "Lungomare", "12", "34121", "Trieste", "IT"),
    ("Iberia Logística SL", "Calle Mayor", "60", "28013", "Madrid", "ES"),
    ("Catalana Textil SA", "Passeig de Gràcia", "5", "08007", "Barcelona", "ES"),
    ("Maple Leaf Mining Corp", "Resource Drive", "3", "T2P 1J9", "Calgary", "CA"),
    ("Pacific Freight Co", "Harbour Lane", "21", "98104", "Seattle", "US"),
)

_FORK = (
    "Pallet racking unit",
    "Forklift battery pack",
    "Conveyor belt segment",
    "Maintenance service contract",
    "Hydraulic lift module",
    "Steel shelving kit",
    "Packaging line upgrade",
    "Cold-storage compressor",
    "Logistics software licence",
    "Safety inspection service",
)


def _fold_umlauts(text: str) -> str:
    table = {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "ß": "ss",
        "Ä": "Ae",
        "Ö": "Oe",
        "Ü": "Ue",
        "é": "e",
        "è": "e",
        "ì": "i",
        "à": "a",
    }
    return "".join(table.get(ch, ch) for ch in text)


def _vary_legal_form(name: str) -> str:
    """Swap a legal-form suffix for a messy-but-recognisable variant."""
    swaps = {
        "GmbH": ("Gmbh", "G.m.b.H", "GMBH"),
        "AG": ("A.G.", "AG."),
        "Inc": ("Inc.", "Incorporated"),
        "LLC": ("L.L.C.", "LLC."),
        "Ltd": ("Ltd.", "Limited"),
        "SARL": ("S.A.R.L.",),
        "SpA": ("S.p.A.", "SPA"),
        "SA": ("S.A.",),
        "SL": ("S.L.",),
        "AS": ("A/S",),
        "OHG": ("oHG",),
        "Corp": ("Corp.", "Corporation"),
        "Co": ("Co.", "Company"),
    }
    for suffix, variants in swaps.items():
        if name.endswith(" " + suffix):
            base = name[: -len(suffix)]
            return base + variants[_stable_hash(name) % len(variants)]
    return name


def _abbreviate(name: str) -> str:
    table = {
        "International": "Intl",
        "Logistik": "Log.",
        "Technologies": "Tech",
        "Solutions": "Sol.",
        "Präzisionstechnik": "Praez.-technik",
        "Datentechnik": "Datentech.",
        "Costruzioni": "Costr.",
        "Logística": "Log.",
        "Énergie": "Energie",
        "Marittima": "Marit.",
    }
    out = name
    for long, short in table.items():
        out = out.replace(long, short)
    return out


def _typo(name: str, rng: random.Random) -> str:
    """Drop or transpose one character — a realistic data-entry typo."""
    if len(name) < 6:
        return name
    i = rng.randrange(2, len(name) - 2)
    if name[i] == " " or name[i + 1] == " ":
        return name
    if rng.random() < 0.5:
        return name[:i] + name[i + 1 :]  # drop
    return name[:i] + name[i + 1] + name[i] + name[i + 2 :]  # transpose


def _name_variant(canonical: str, rng: random.Random) -> str:
    """A noisy but human-recognisable variant of an organisation name."""
    name = canonical
    transforms = []
    if rng.random() < 0.6:
        transforms.append(_fold_umlauts)
    if rng.random() < 0.5:
        transforms.append(_vary_legal_form)
    if rng.random() < 0.4:
        transforms.append(_abbreviate)
    rng.shuffle(transforms)
    for fn in transforms:
        name = fn(name)
    if rng.random() < 0.35:
        name = _typo(name, rng)
    return name.strip()


def _street_variant(street: str, rng: random.Random) -> str:
    out = _fold_umlauts(street) if rng.random() < 0.5 else street
    replacements = (("strasse", "str."), ("Strasse", "Str."), ("Avenue", "Ave"))
    if rng.random() < 0.6:
        for long, short in replacements:
            out = out.replace(long, short)
    return out


def main() -> None:
    rng = random.Random(SEED)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    customers: list[dict[str, str]] = []
    addresses: list[dict[str, str]] = []
    sales_docs: list[dict[str, str]] = []
    items: list[dict[str, str]] = []

    # VATRegistration assignment (Milestone 10, spec 0078). A customer's VAT is
    # derived from a *firm-identity seed*: the canonical entity name for the
    # duplicate-bearing entities (so every duplicate shares one VAT and multi-field
    # ER never splits a genuine merge), and the unique customer id for the
    # hand-appended firms that share a name but are genuinely distinct (so they get
    # DISTINCT VATs and ER can tell them apart). ``_seen`` makes a hash collision
    # between two distinct seeds a loud build failure, not a silent over-merge.
    _seen: dict[str, str] = {}

    def _assign_vat(seed: str, country: str) -> str:
        vat = f"{country}{_stable_hash(seed) % 1_000_000_000:09d}"
        prior = _seen.setdefault(vat, seed)
        if prior != seed:
            raise ValueError(f"VAT collision: {vat} from {seed!r} and {prior!r}")
        return vat

    # --- Spotlight entity: fixed values the demo question is authored against. ---
    # Kept deterministic and out of the random stream so its ids/figures are stable
    # references for knowledge.py. Customer master and address master disagree on
    # the name ("Müller Logistik GmbH" vs "Mueller Logistik Gmbh") on purpose.
    customers.append(
        {
            "Customer": "0010000007",
            "CustomerName": "Müller Logistik GmbH",
            "AddressID": "A0007",
            "CustomerAccountGroup": "KUNA",
            "Country": "DE",
            "VATRegistration": _assign_vat("Müller Logistik GmbH", "DE"),
        }
    )
    addresses.append(
        {
            "AddressID": "A0007",
            "OrganizationName": "Mueller Logistik Gmbh",
            "StreetName": "Industriestr.",
            "HouseNumber": "12",
            "PostalCode": "20095",
            "CityName": "Hamburg",
            "Country": "DE",
        }
    )
    _add_sales_doc(
        sales_docs,
        items,
        doc_id="0000500001",
        customer="0010000007",
        date="2026-02-10",
        currency="EUR",
        lines=[
            ("Forklift battery pack", "4", "12000.00"),
            ("Maintenance service contract", "1", "8000.00"),
        ],
    )
    _add_sales_doc(
        sales_docs,
        items,
        doc_id="0000500002",
        customer="0010000007",
        date="2026-03-05",
        currency="EUR",
        lines=[("Conveyor belt segment", "5", "25000.00")],
    )

    # --- The rest: deterministic noisy views of the true entities. ---------------
    # Customer ids start at 1001 so they cannot collide with the reserved
    # spotlight id (0010000007) — a collision would silently duplicate a key.
    next_customer = 1001
    next_address = 1
    next_doc = 3
    currency_by_country = {
        "DE": "EUR",
        "AT": "EUR",
        "FR": "EUR",
        "IT": "EUR",
        "ES": "EUR",
        "CH": "CHF",
        "GB": "GBP",
        "US": "USD",
        "CA": "CAD",
        "NO": "NOK",
    }

    while len(customers) < TARGET_CUSTOMERS:
        entity = _ENTITIES[rng.randrange(len(_ENTITIES))]
        canonical, street, house, postal, city, country = entity
        # Some entities spawn duplicate customers — the core ER challenge.
        dupes = 1 if rng.random() < 0.6 else 2
        for _ in range(dupes):
            if len(customers) >= TARGET_CUSTOMERS:
                break
            cust_id = f"001000{next_customer:04d}"
            addr_id = f"A1{next_address:03d}"
            next_customer += 1
            next_address += 1
            customers.append(
                {
                    "Customer": cust_id,
                    "CustomerName": _name_variant(canonical, rng),
                    "AddressID": addr_id,
                    "CustomerAccountGroup": rng.choice(("KUNA", "KUNL", "CPD")),
                    "Country": country,
                    # Seed on the canonical name so every duplicate of this firm
                    # shares one VAT (a genuine merge is never split by the key).
                    "VATRegistration": _assign_vat(canonical, country),
                }
            )
            addresses.append(
                {
                    "AddressID": addr_id,
                    "OrganizationName": _name_variant(canonical, rng),
                    "StreetName": _street_variant(street, rng),
                    "HouseNumber": house,
                    "PostalCode": postal,
                    "CityName": _fold_umlauts(city) if rng.random() < 0.4 else city,
                    "Country": country,
                }
            )

    # Sales documents spread across customers, each with 1–3 line items.
    for _ in range(80):
        cust = customers[rng.randrange(len(customers))]
        doc_id = f"00005000{next_doc:02d}"
        next_doc += 1
        currency = currency_by_country.get(cust["Country"], "EUR")
        month = rng.randrange(1, 7)
        day = rng.randrange(1, 28)
        lines = [
            (
                rng.choice(_FORK),
                str(rng.randrange(1, 12)),
                f"{rng.randrange(1, 40) * 500}.00",
            )
            for _ in range(rng.randrange(1, 4))
        ]
        _add_sales_doc(
            sales_docs,
            items,
            doc_id=doc_id,
            customer=cust["Customer"],
            date=f"2026-{month:02d}-{day:02d}",
            currency=currency,
            lines=lines,
        )

    # --- Mixed-currency entity: a multinational that transacts in two currencies. -
    # Fixed (no RNG) and appended last, so it cannot perturb the deterministic rows
    # above. It exists so the cross-source aggregate has a real "refuse to sum
    # across currencies" case (a single customer with both an EUR and a USD order).
    customers.append(
        {
            "Customer": "0010000008",
            "CustomerName": "Atlas Trading GmbH",
            "AddressID": "A0008",
            "CustomerAccountGroup": "KUNA",
            "Country": "DE",
            "VATRegistration": _assign_vat("Atlas Trading GmbH", "DE"),
        }
    )
    addresses.append(
        {
            "AddressID": "A0008",
            "OrganizationName": "Atlas Trading GmbH",
            "StreetName": "Handelsweg",
            "HouseNumber": "3",
            "PostalCode": "60311",
            "CityName": "Frankfurt",
            "Country": "DE",
        }
    )
    _add_sales_doc(
        sales_docs,
        items,
        doc_id="0000500900",
        customer="0010000008",
        date="2026-02-20",
        currency="EUR",
        lines=[("Pallet racking unit", "10", "15000.00")],
    )
    _add_sales_doc(
        sales_docs,
        items,
        doc_id="0000500901",
        customer="0010000008",
        date="2026-04-02",
        currency="USD",
        lines=[("Packaging line upgrade", "1", "18000.00")],
    )

    # --- Disambiguation pair: two DISTINCT firms with an IDENTICAL name. ----------
    # Milestone 9 (spec 0075): name-only ER over-merges these into one entity (they
    # share their distinctive identity token), so the ambiguous-name question resolves
    # to a single wrong entity and answers it; multi-field ER (name + address) splits
    # them on their DIFFERENT addresses, so the question correctly refuses as
    # ambiguous. Fixed (no RNG) and appended last, so existing rows stay byte-identical.
    # They carry NO sales orders — the demonstration is the customer-master ambiguity,
    # and orders would generate a same-name synthetic compare case.
    for cust_id, addr_id, street, house, postal, city in (
        ("0010000009", "A0009", "Hafenstrasse", "7", "20457", "Hamburg"),
        ("0010000010", "A0010", "Maximilianstrasse", "35", "80539", "Munich"),
    ):
        customers.append(
            {
                "Customer": cust_id,
                "CustomerName": "Hanseatic Trading GmbH",
                "AddressID": addr_id,
                "CustomerAccountGroup": "KUNA",
                "Country": "DE",
                # Two DISTINCT firms sharing a name → seed on the unique customer id
                # so they get DISTINCT VATs (Milestone 9 split them on address; the
                # key splits them too, the stronger signal).
                "VATRegistration": _assign_vat(cust_id, "DE"),
            }
        )
        addresses.append(
            {
                "AddressID": addr_id,
                "OrganizationName": "Hanseatic Trading GmbH",
                "StreetName": street,
                "HouseNumber": house,
                "PostalCode": postal,
                "CityName": city,
                "Country": "DE",
            }
        )

    # --- Same-name / SAME-address pair: the registration-key floor. ----------------
    # Milestone 10 (spec 0079): two DISTINCT firms with an IDENTICAL name AND an
    # IDENTICAL address (Am Kanal 5, 14467 Potsdam) — the floor name + address ER
    # (Milestone 9) cannot reach: the address AGREES, so it corroborates a merge and the
    # firms over-merge. Only the exact registration key (their DIFFERENT VATs) splits
    # them. The two records use DISTINCT AddressIDs that carry the SAME postal address
    # (each firm's own master record), so each address node carries its own firm's key
    # and the two split into two connected components. Fixed (no RNG) and appended last,
    # so existing rows stay byte-identical. No sales orders (as Milestone 9), so the
    # demonstration is the customer-master ambiguity, not a same-name compare case.
    for cust_id, addr_id in (("0010000011", "A0011"), ("0010000012", "A0012")):
        customers.append(
            {
                "Customer": cust_id,
                "CustomerName": "Havel Kontor GmbH",
                "AddressID": addr_id,
                "CustomerAccountGroup": "KUNA",
                "Country": "DE",
                # Two DISTINCT firms, same name AND same address → seed on the unique
                # customer id so they get DISTINCT VATs (the only signal that splits
                # them; address agrees, name agrees).
                "VATRegistration": _assign_vat(cust_id, "DE"),
            }
        )
        addresses.append(
            {
                "AddressID": addr_id,
                "OrganizationName": "Havel Kontor GmbH",
                "StreetName": "Am Kanal",
                "HouseNumber": "5",
                "PostalCode": "14467",
                "CityName": "Potsdam",
                "Country": "DE",
            }
        )

    _write_csv(
        "I_Customer.csv",
        customers,
        [
            "Customer",
            "CustomerName",
            "AddressID",
            "CustomerAccountGroup",
            "Country",
            "VATRegistration",
        ],
    )
    _write_csv(
        "I_AddrOrgNamePostalAddress.csv",
        addresses,
        [
            "AddressID",
            "OrganizationName",
            "StreetName",
            "HouseNumber",
            "PostalCode",
            "CityName",
            "Country",
        ],
    )
    _write_csv(
        "I_SalesDocument.csv",
        sales_docs,
        [
            "SalesDocument",
            "SoldToParty",
            "ShipToParty",
            "BillToParty",
            "PayerParty",
            "SalesDocumentDate",
            "TotalNetAmount",
            "TransactionCurrency",
        ],
    )
    _write_csv(
        "I_SalesDocumentItem.csv",
        items,
        [
            "SalesDocument",
            "SalesDocumentItem",
            "Material",
            "SalesDocumentItemText",
            "OrderQuantity",
            "NetAmount",
            "TransactionCurrency",
        ],
    )

    _write_manifest(
        {
            "I_Customer.csv": len(customers),
            "I_AddrOrgNamePostalAddress.csv": len(addresses),
            "I_SalesDocument.csv": len(sales_docs),
            "I_SalesDocumentItem.csv": len(items),
        }
    )
    total = len(customers) + len(addresses) + len(sales_docs) + len(items)
    print(f"Wrote {total} rows across 4 tables to {OUT_DIR}")


def _add_sales_doc(
    sales_docs: list[dict[str, str]],
    items: list[dict[str, str]],
    *,
    doc_id: str,
    customer: str,
    date: str,
    currency: str,
    lines: list[tuple[str, str, str]],
) -> None:
    total = sum(float(net) for _, _, net in lines)
    sales_docs.append(
        {
            "SalesDocument": doc_id,
            "SoldToParty": customer,
            "ShipToParty": customer,
            "BillToParty": customer,
            "PayerParty": customer,
            "SalesDocumentDate": date,
            "TotalNetAmount": f"{total:.2f}",
            "TransactionCurrency": currency,
        }
    )
    for n, (text, qty, net) in enumerate(lines, start=1):
        items.append(
            {
                "SalesDocument": doc_id,
                "SalesDocumentItem": str(n * 10),
                "Material": f"MAT-{_stable_hash(text) % 9000 + 1000}",
                "SalesDocumentItemText": text,
                "OrderQuantity": qty,
                "NetAmount": net,
                "TransactionCurrency": currency,
            }
        )


def _write_csv(name: str, rows: list[dict[str, str]], header: list[str]) -> None:
    path = OUT_DIR / name
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_manifest(row_counts: dict[str, int]) -> None:
    manifest = {
        "dataset": "salt_synthetic",
        "synthetic": True,
        "schema_reference": (
            "SAP SALT (Sales Autocompletion Linked Business Tables), arXiv:2501.03413"
        ),
        "generator": "scripts/generate_salt_synthetic.py",
        "seed": SEED,
        "snapshot_date": SNAPSHOT_DATE,
        "row_counts": row_counts,
    }
    (OUT_DIR / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
