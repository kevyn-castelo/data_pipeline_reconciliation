"""Conciliação bancária explicável dos candidatos Uber/AP; não altera o ERP.

Uso: .venv/Scripts/python.exe bank_reconciliation.py --pipeline-output output
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import unicodedata
from collections import Counter
from datetime import datetime
from decimal import Decimal
from itertools import combinations
from pathlib import Path

import duckdb


ROOT = Path(__file__).resolve().parent
CUTOVER_BLOCKERS = {"competence_before_automation_start", "due_date_in_past"}


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode().upper()
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9 ]", " ", value)).strip()


def cents(value) -> int:
    return int(Decimal(str(value)) * 100)


def money(cents_value: int) -> str:
    return f"{Decimal(cents_value) / 100:.2f}"


def bank_entries(path: Path):
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    encoding = "utf-8-sig"
    try:
        text = data.decode(encoding)
    except UnicodeDecodeError:
        encoding = "cp1252"
        text = data.decode(encoding)
    lines = text.splitlines()
    header = next(i for i, line in enumerate(lines) if line.lower().startswith("data;lan"))
    entries = []
    for physical_line, row in enumerate(csv.reader(lines[header + 1 :], delimiter=";"), start=header + 2):
        if len(row) < 5 or not row[3].strip():
            continue  # opening/daily balances are not bank movements
        value = Decimal(row[3].replace(".", "").replace(",", "."))
        entries.append({
            "bank_id": f"{digest[:16]}:{physical_line}", "file_sha256": digest,
            "source_file": path.name, "source_line": physical_line,
            "date": datetime.strptime(row[0], "%d/%m/%Y").date(),
            "description": row[1].strip(), "origin": row[2].strip(),
            "cents": cents(value),
        })
    return entries


def candidates(db: Path):
    con = duckdb.connect(str(db), read_only=True)
    try:
        rows = con.execute("""
            select id_externo, tipo, beneficiario_nome, num_documento, data_vencimento,
                   competence, valor_total_candidato, final_release_blockers
            from int_ap_release_gate order by tipo, competence, beneficiario_nome
        """).fetchall()
        visa = con.execute("""
            select transaction_id, trip_id, request_ts_local::date, amount_brl,
                   payment_route_status
            from int_transaction_enrichment
            where payment_route_status='needs_client_card_destination'
            order by transaction_id
        """).fetchall()
    finally:
        con.close()
    titles = []
    for row in rows:
        title_id, kind, name, document, due, competence, value, blockers = row
        titles.append({"id": title_id, "kind": kind, "name": name or "", "document": document or "",
                       "due": due, "competence": competence, "cents": cents(value) if value is not None else None,
                       "blockers": blockers or [], "bank_ids": [], "status": "unmatched", "confidence": "none",
                       "difference_cents": None, "rule": "", "duplicate_bank_ids": []})
    visa_rows = [{"id": r[0], "trip_id": r[1], "date": r[2], "cents": cents(r[3]), "route": r[4]} for r in visa if r[3] is not None]
    return titles, visa_rows


def in_window(entry, title, before=2, after=45):
    if title["due"] is None:
        return False
    days = (entry["date"] - title["due"]).days
    return -before <= days <= after


def set_match(title, entries, status, confidence, rule, difference=None):
    title.update(bank_ids=[e["bank_id"] for e in entries], status=status,
                 confidence=confidence, difference_cents=difference, rule=rule)


def reconcile(titles, visa_rows, entries):
    debits = [e for e in entries if e["cents"] < 0]
    used = set()
    duplicate = set()
    historical = [t for t in titles if t["kind"] == "REEMBOLSO_COLABORADOR"
                  and t["cents"] is not None and set(t["blockers"]) <= CUTOVER_BLOCKERS]
    for title in titles:
        if title["kind"] == "REEMBOLSO_COLABORADOR" and title not in historical:
            title.update(status="held_unpayable", rule="financial_or_registry_blocker")

    # Exact PIX: beneficiary prefix, cents and payment window must point to one title.
    for entry in sorted(debits, key=lambda e: (e["date"], e["source_line"])):
        if not entry["description"].upper().startswith("PIX TRANSF "):
            continue
        prefix = norm(entry["description"][len("PIX TRANSF ") :])
        possible = [t for t in historical if norm(t["name"]).startswith(prefix)
                    and t["cents"] == -entry["cents"] and in_window(entry, t)]
        if len(possible) != 1:
            continue
        title = possible[0]
        if title["bank_ids"]:
            duplicate.add(entry["bank_id"])
            title["duplicate_bank_ids"].append(entry["bank_id"])
        else:
            set_match(title, [entry], "matched_exact", "high", "unique_prefix_amount_due_window", 0)
            used.add(entry["bank_id"])

    # One PIX may settle two months for the same beneficiary.
    for entry in debits:
        if entry["bank_id"] in used or entry["bank_id"] in duplicate or not entry["description"].upper().startswith("PIX TRANSF "):
            continue
        prefix = norm(entry["description"][len("PIX TRANSF ") :])
        options = [t for t in historical if not t["bank_ids"] and norm(t["name"]).startswith(prefix)
                   and in_window(entry, t)]
        pairs = [pair for pair in combinations(options, 2)
                 if norm(pair[0]["name"]) == norm(pair[1]["name"])
                 and pair[0]["cents"] + pair[1]["cents"] == -entry["cents"]]
        if len(pairs) == 1:
            for title in pairs[0]:
                set_match(title, [entry], "matched_aggregate", "medium", "unique_same_beneficiary_two_title_sum", 0)
            used.add(entry["bank_id"])

    # Cent-level differences are review items, never automatic write-offs.
    for entry in debits:
        if entry["bank_id"] in used or entry["bank_id"] in duplicate or not entry["description"].upper().startswith("PIX TRANSF "):
            continue
        prefix = norm(entry["description"][len("PIX TRANSF ") :])
        possible = [t for t in historical if not t["bank_ids"] and norm(t["name"]).startswith(prefix)
                    and in_window(entry, t) and abs(-entry["cents"] - t["cents"]) <= 5]
        if len(possible) == 1:
            title = possible[0]
            set_match(title, [entry], "matched_with_difference", "medium",
                      "unique_prefix_due_window_within_5_cents", -entry["cents"] - title["cents"])
            used.add(entry["bank_id"])

    for title in [t for t in titles if t["kind"] == "FATURA_FORNECEDOR"]:
        possible = [e for e in debits if e["bank_id"] not in used
                    and norm(e["description"]).startswith("SISPAG BOLETO UBER")
                    and in_window(e, title, before=2, after=10)]
        if len(possible) == 1 and title["cents"] is not None:
            entry = possible[0]
            diff = -entry["cents"] - title["cents"]
            set_match(title, [entry], "matched_exact" if diff == 0 else "matched_with_difference",
                      "high" if diff == 0 else "medium",
                      "uber_boleto_name_due_window_amount" if diff == 0 else "uber_boleto_amount_difference_requires_support",
                      diff)
            used.add(entry["bank_id"])

    visa_matches = []
    for source in visa_rows:
        possible = [e for e in debits if e["bank_id"] not in used and e["description"].upper().startswith("UBER *TRIP")
                    and -e["cents"] == source["cents"] and abs((e["date"] - source["date"]).days) <= 3]
        if len(possible) == 1:
            entry = possible[0]
            visa_matches.append({"source_transaction_id": source["id"], "trip_id": source["trip_id"],
                                 "bank_id": entry["bank_id"], "value": money(source["cents"]),
                                 "status": "card_debit_matched_classification_pending", "confidence": "medium"})
            used.add(entry["bank_id"])

    for title in historical:
        if not title["bank_ids"]:
            title.update(status="open_as_of_statement_end", rule="no_unique_bank_debit_found")
    for title in titles:
        if title["kind"] == "FATURA_FORNECEDOR" and not title["bank_ids"]:
            title.update(status="no_bank_match", rule="no_unique_uber_boleto_found")

    unmatched = []
    for entry in debits:
        if entry["bank_id"] in used:
            continue
        category = "duplicate_payment" if entry["bank_id"] in duplicate else (
            "unmatched_uber_or_pix_debit" if entry["description"].startswith("PIX TRANSF")
            or "UBER" in entry["description"].upper() else "outside_uber_ap_scope")
        unmatched.append({**entry, "category": category})
    return titles, visa_matches, unmatched


def write_csv(path, rows, columns):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pipeline-output", type=Path, default=ROOT / "output")
    parser.add_argument("--bank", type=Path, default=ROOT / "data/extrato_itau_cc_2026-07_a_2026-09.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "reconciliation")
    args = parser.parse_args()
    db = args.pipeline_output / "canonical.duckdb"
    if not db.is_file() or not args.bank.is_file():
        parser.error("Banco canônico ou extrato bancário ausente")
    out = args.output.resolve()
    if out.exists() and not (out / ".bank_reconciliation_output").is_file():
        parser.error("Pasta de saída existente sem marcador de conciliação")
    out.mkdir(parents=True, exist_ok=True)
    (out / ".bank_reconciliation_output").write_text("Resultados reproduzíveis; sem baixa no ERP.\n", encoding="utf-8")
    entries = bank_entries(args.bank)
    titles, visa_rows = candidates(db)
    titles, visa_matches, unmatched = reconcile(titles, visa_rows, entries)
    by_id = {e["bank_id"]: e for e in entries}
    title_rows = []
    pair_rows = []
    for title in titles:
        title_rows.append({"id_externo": title["id"], "tipo": title["kind"], "competencia": title["competence"],
                           "beneficiario": title["name"], "num_documento": title["document"],
                           "vencimento": str(title["due"] or ""), "valor_titulo": money(title["cents"]) if title["cents"] is not None else "",
                           "status": title["status"], "confianca": title["confidence"], "diferenca": money(title["difference_cents"]) if title["difference_cents"] is not None else "",
                           "regra": title["rule"], "bank_ids": "|".join(title["bank_ids"]),
                           "pago_mais_de_uma_vez": bool(title["duplicate_bank_ids"]),
                           "bank_ids_duplicados": "|".join(title["duplicate_bank_ids"]),
                           "bloqueios_ap": "|".join(title["blockers"]), "erp_baixa_confirmada": "nao_verificada"})
        for bank_id in title["bank_ids"]:
            entry = by_id[bank_id]
            pair_rows.append({"id_externo": title["id"], "bank_id": bank_id, "bank_date": str(entry["date"]),
                              "bank_description": entry["description"], "bank_value": money(entry["cents"]),
                              "status": title["status"], "confianca": title["confidence"], "regra": title["rule"]})
    write_csv(out / "bank_reconciliation.csv", title_rows,
              ["id_externo", "tipo", "competencia", "beneficiario", "num_documento", "vencimento", "valor_titulo",
               "status", "confianca", "diferenca", "regra", "bank_ids", "pago_mais_de_uma_vez",
               "bank_ids_duplicados", "bloqueios_ap", "erp_baixa_confirmada"])
    write_csv(out / "bank_match_pairs.csv", pair_rows,
              ["id_externo", "bank_id", "bank_date", "bank_description", "bank_value", "status", "confianca", "regra"])
    write_csv(out / "bank_unmatched_debits.csv",
              [{"bank_id": e["bank_id"], "source_file": e["source_file"], "source_line": e["source_line"],
                "date": str(e["date"]), "description": e["description"], "value": money(e["cents"]),
                "category": e["category"]} for e in unmatched],
              ["bank_id", "source_file", "source_line", "date", "description", "value", "category"])
    write_csv(out / "bank_card_route_matches.csv", visa_matches,
              ["source_transaction_id", "trip_id", "bank_id", "value", "status", "confidence"])
    summary = {"bank_file_sha256": hashlib.sha256(args.bank.read_bytes()).hexdigest(),
               "reconciliation_code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "pipeline_code_sha256": json.loads((args.pipeline_output / "run_summary.json").read_text(encoding="utf-8"))["code_sha256"],
               "title_status_counts": dict(sorted(Counter(t["status"] for t in titles).items())),
               "unmatched_debit_counts": dict(sorted(Counter(e["category"] for e in unmatched).items())),
               "paid_more_than_once_title_count": sum(bool(t["duplicate_bank_ids"]) for t in titles),
               "visa_route_match_count": len(visa_matches), "bank_movement_count": len(entries),
               "note": "Evidência de extrato; confirmações de ERP, encargos e classificação ainda requeridas."}
    (out / "bank_reconciliation_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
