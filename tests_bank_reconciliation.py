"""Oráculo do parecer para o extrato de julho a setembro de 2026."""

import argparse
from pathlib import Path
from copy import deepcopy
from datetime import date
from decimal import Decimal

from bank_reconciliation import bank_entries, candidates, reconcile, report_rows


ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument("--pipeline-output", type=Path, default=ROOT / "output")
titles, visa = candidates(parser.parse_args().pipeline_output / "canonical.duckdb")
titles, visa_matches, unmatched = reconcile(
    titles, visa, bank_entries(ROOT / "data/extrato_itau_cc_2026-07_a_2026-09.csv")
)
reimbursements = [t for t in titles if t["kind"] == "REEMBOLSO_COLABORADOR"]
invoices = [t for t in titles if t["kind"] == "FATURA_FORNECEDOR"]

assert sum(t["primary_status"] == "matched_exact" for t in reimbursements) == 12
assert sum(t["status"] == "matched_with_difference" for t in reimbursements) == 1
assert sum(t["status"] == "matched_aggregate" for t in reimbursements) == 2
assert sum(t["status"] == "open_as_of_statement_end" for t in reimbursements) == 3
assert sorted(t["cents"] for t in reimbursements if t["status"] == "open_as_of_statement_end") == [10280, 14268, 14623]
assert [t["difference_cents"] for t in reimbursements if t["status"] == "matched_with_difference"] == [-1]
assert sum(bool(t["duplicate_bank_ids"]) for t in reimbursements) == 1
assert [e["cents"] for e in unmatched if e["category"] == "duplicate_payment"] == [-7378]
assert sorted(t["difference_cents"] for t in invoices) == [0, 30527]
assert len(visa_matches) == 1 and visa_matches[0]["value"] == "33.20"
assert sum(t["cents"] for t in reimbursements) == 160875
assert sum(t['paid_cents'] or 0 for t in reimbursements) == 121703
assert sum(t['duplicate_cents'] for t in reimbursements) == 7378
entries = bank_entries(ROOT / 'data/extrato_itau_cc_2026-07_a_2026-09.csv')
title_rows, pairs, _ = report_rows(titles, entries)
marcos = next(r for r in title_rows if r['status']=='paid_more_than_once')
assert (marcos['valor_titulo'], marcos['valor_bancario_atribuido_total'], marcos['diferenca_incluindo_duplicidade']) == ('73.78','147.56','73.78')
assert sum(Decimal(r['valor_atribuido_titulo']) for r in pairs) == Decimal('31128.89')
assert all(r['valor_pagamento_principal']=='' for r in title_rows if r['status']=='open_as_of_statement_end')

# Regressões: nomes iguais não provam a mesma pessoa; bloqueio de AP não esconde pagamento.
def debit(value, description='PIX TRANSF CAMILA ROCHA NETO', bank_id='synthetic:1'):
    return dict(bank_id=bank_id, date=date(2026,9,15), source_line=1,
                description=description, origin='synthetic', cents=-value)

original,_ = candidates(ROOT / 'output/canonical.duckdb')
cams = [deepcopy(t) for t in original if t['name']=='Camila Rocha Neto']
result,_,unmatched = reconcile(cams, [], [debit(26268)])
assert all(t['status']=='needs_review' and not t['bank_ids'] for t in result)
assert unmatched[0]['category']=='needs_review'

# Mesmo nome e valor em duas pessoas deve continuar ambíguo no 1:1.
cams[1]['cents']=cams[0]['cents']
result,_,_ = reconcile(cams, [], [debit(cams[0]['cents'])])
assert all(t['status']=='needs_review' for t in result)

mariana = [deepcopy(t) for t in original if t['name']=='Mariana Lopes da Silva' and t['competence']=='2026-08']
result,_,_ = reconcile(mariana, [], [debit(10280,'PIX TRANSF MARIANA LOPES DA')])
assert result[0]['status']=='matched_exact' and result[0]['blockers']

invoice = [deepcopy(t) for t in original if t['kind']=='FATURA_FORNECEDOR' and t['competence']=='2026-08']
result,_,unmatched = reconcile(invoice, [], [debit(3000000,'SISPAG BOLETO UBER DO BRASIL TECN')])
assert result[0]['status']=='needs_review' and result[0]['paid_cents'] is None
assert unmatched[0]['category']=='needs_review'

# Pagamento agrupado conserva caixa por movimento, mesmo que a ordem de entrada mude.
fresh,visa = candidates(ROOT / 'output/canonical.duckdb')
again,_,_ = reconcile(list(reversed(fresh)), visa, list(reversed(entries)))
assert {t['id']:(t['status'],t['paid_cents']) for t in again} == {t['id']:(t['status'],t['paid_cents']) for t in titles}
print('bank_reconciliation_oracle_and_regressions=PASS')
