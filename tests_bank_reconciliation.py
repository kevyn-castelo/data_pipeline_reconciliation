"""Oráculo do parecer para o extrato de julho a setembro de 2026."""

from pathlib import Path

from bank_reconciliation import bank_entries, candidates, reconcile


ROOT = Path(__file__).resolve().parent
titles, visa = candidates(ROOT / "output/canonical.duckdb")
titles, visa_matches, unmatched = reconcile(
    titles, visa, bank_entries(ROOT / "data/extrato_itau_cc_2026-07_a_2026-09.csv")
)
reimbursements = [t for t in titles if t["kind"] == "REEMBOLSO_COLABORADOR"]
invoices = [t for t in titles if t["kind"] == "FATURA_FORNECEDOR"]

assert sum(t["status"] == "matched_exact" for t in reimbursements) == 12
assert sum(t["status"] == "matched_with_difference" for t in reimbursements) == 1
assert sum(t["status"] == "matched_aggregate" for t in reimbursements) == 2
assert sum(t["status"] == "open_as_of_statement_end" for t in reimbursements) == 1
assert sum(t["status"] == "held_unpayable" for t in reimbursements) == 2
assert [t["cents"] for t in reimbursements if t["status"] == "open_as_of_statement_end"] == [14623]
assert [t["difference_cents"] for t in reimbursements if t["status"] == "matched_with_difference"] == [-1]
assert sum(bool(t["duplicate_bank_ids"]) for t in reimbursements) == 1
assert [e["cents"] for e in unmatched if e["category"] == "duplicate_payment"] == [-7378]
assert sorted(t["difference_cents"] for t in invoices) == [0, 30527]
assert len(visa_matches) == 1 and visa_matches[0]["value"] == "33.20"
assert sum(t["cents"] for t in reimbursements if t["status"] not in ("held_unpayable",)) == 136327
print("bank_reconciliation_oracle=PASS")
