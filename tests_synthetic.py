"""Small contract checks for the canonical core. Run with the project .venv Python."""
from __future__ import annotations

import csv
from decimal import Decimal
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import duckdb
import openpyxl

from run import CANONICAL_FIELDS, ROOT, dbt_cli_for_python


# Outside the published output/: test artifacts must never block or pollute a real publication.
TEST_ROOT = ROOT / ".test_output" / "synthetic"
TEST_MARKER = TEST_ROOT / ".synthetic-owned"
assert dbt_cli_for_python(Path('venv') / 'bin' / 'python', 'posix') == Path('venv') / 'bin' / 'dbt'
assert dbt_cli_for_python(Path('venv') / 'Scripts' / 'python.exe', 'nt') == Path('venv') / 'Scripts' / 'dbt.exe'
HEADER_BY_FIELD = {field: aliases[0] for field, aliases in CANONICAL_FIELDS.items()}
HEADERS = list(HEADER_BY_FIELD.values())


def row(trip, ts, kind="Adjustment", amount="1.00", request="12:00:00 PM", **overrides):
    values = {name: "" for name in HEADERS}
    base = {
        "trip_id": trip, "transaction_ts_utc": ts,
        "request_date_utc": "08/20/2026", "request_time_utc": request,
        "request_date_local": "08/20/2026", "request_time_local": request,
        "dropoff_date_utc": "08/20/2026", "dropoff_time_utc": "01:00:00 PM",
        "dropoff_date_local": "08/20/2026", "dropoff_time_local": "10:00:00 AM",
        "request_utc_offset": "-03:00", "first_name": "Teste", "last_name": "Contrato",
        "email": "teste@example.com", "uber_employee_id_raw": "001004", "uber_group": "Operacao",
        "service": "Travel | UberX", "program": "Corp", "city": "Curitiba", "country": "Brazil",
        "expense_code": " adm ", "expense_memo": "", "payment_method_raw": "VISA - 0042",
        "transaction_type": kind, "amount_local": amount, "local_currency": "BRL",
        "tips_brl": "0.00", "total_fare_brl": "1.00", "employee_paid_brl": "0.00",
        "amount_brl": amount, "uber_invoice_number": "--", "requester": "Solicitado por: comprador@example.com",
    }
    base.update(overrides)
    for field, value in base.items():
        values[HEADER_BY_FIELD[field]] = value
    return [values[h] for h in HEADERS]


def write_csv(folder: Path, name: str, rows, reverse=False):
    folder.mkdir(parents=True, exist_ok=True)
    headers = list(reversed(HEADERS)) if reverse else HEADERS
    path = folder / name
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Company:", "Industria Madeireira Parana Ltda"])
        w.writerow(["Report Date:", "2026-08-31 23:00:00"])
        w.writerow(["Transactions"])
        w.writerow(headers)
        for values in rows:
            record = dict(zip(HEADERS, values))
            w.writerow([record[h] for h in headers])
    return path


def call_pipeline(input_dir: Path, output_dir: Path, resolutions: Path | None = None,
                  expect_ok=True, as_of_date="2026-01-01", first_competence="2026-01",
                  issued_ledger: Path | None = None, extra_args=()):
    cmd = [sys.executable, str(ROOT / "run.py"), "--input", str(input_dir), "--output", str(output_dir),
           "--as-of-date", as_of_date, "--first-competence", first_competence, *extra_args]
    if resolutions:
        cmd += ["--resolutions", str(resolutions)]
    if issued_ledger:
        cmd += ["--issued-ledger", str(issued_ledger)]
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if expect_ok and p.returncode:
        raise AssertionError(p.stdout + "\n" + p.stderr)
    if not expect_ok and p.returncode == 0:
        raise AssertionError("A execução deveria falhar (D8).")
    return p


def read_rows(db_path, sql):
    c = duckdb.connect(str(db_path), read_only=True)
    try:
        return c.execute(sql).fetchall()
    finally:
        c.close()


def make_decision(db, trip, action, chosen=None):
    records = read_rows(db, f"select business_key, occurrence_ids from int_transactions where trip_id='{trip}'")
    assert len(records) == 1, (trip, records)
    key, ids = records[0]
    if isinstance(ids, str):
        ids = json.loads(ids)
    return [key, json.dumps(sorted(ids), separators=(",", ":")), action, chosen or "", "synthetic_test", "2026-09-27T00:00:00Z", "contract fixture"]


def save_seed(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["business_key", "occurrence_ids_seen", "action", "chosen_occurrence_id", "decided_by", "decided_at", "reason"])
        w.writerows(rows)


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_aux_csv(path, headers, records, delimiter=","):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=delimiter)
        w.writerow(headers)
        w.writerows(records)


def write_aux_xlsx(path, headers, records, sheet="Sheet"):
    path.parent.mkdir(parents=True, exist_ok=True)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet
    ws.append(headers)
    for record in records:
        ws.append(record)
    wb.save(path)


def make_stage3_fixture(folder: Path, include_bad_component=False, overprecision=False, partial_period=False, with_cards=False):
    input_dir = folder / "input"
    good = row("ap-good", "21/07/26 12:00:00", amount="10.00", kind="Fare",
               payment_method_raw="Periodic Billing", expense_code="GOOD",
               request_date_utc="07/21/2026", request_time_utc="09:00:00 AM",
               request_date_local="07/21/2026", request_time_local="09:00:00 AM",
               dropoff_date_utc="07/21/2026", dropoff_time_utc="09:30:00 AM",
               dropoff_date_local="07/21/2026", dropoff_time_local="06:30:00 AM",
               email="alice@corp.example")
    tx_rows = [good]
    if with_cards:
        # Mixed-case brand of a registered corporate credit card must route by registry type, never to reimbursement.
        tx_rows.append(row("ap-amex", "21/07/26 14:00:00", amount="7.00", kind="Fare",
                           payment_method_raw="Amex - 3008", expense_code="GOOD",
                           request_date_utc="07/21/2026", request_time_utc="11:00:00 AM",
                           request_date_local="07/21/2026", request_time_local="11:00:00 AM",
                           dropoff_date_utc="07/21/2026", dropoff_time_utc="11:30:00 AM",
                           dropoff_date_local="07/21/2026", dropoff_time_local="08:30:00 AM",
                           email="alice@corp.example"))
        # Unregistered card = paid by the employee: one reimbursement title for the local month.
        tx_rows.append(row("ap-personal", "22/07/26 14:00:00", amount="7.50", kind="Fare",
                           payment_method_raw="MASTERCARD - 1111", expense_code="GOOD",
                           request_date_utc="07/22/2026", request_time_utc="11:00:00 AM",
                           request_date_local="07/22/2026", request_time_local="11:00:00 AM",
                           dropoff_date_utc="07/22/2026", dropoff_time_utc="11:30:00 AM",
                           dropoff_date_local="07/22/2026", dropoff_time_local="08:30:00 AM",
                           email="alice@corp.example"))
    total = "10,001" if overprecision else "10,00"
    if include_bad_component:
        bad = row("ap-bad-map", "21/07/26 13:00:00", amount="10.00", kind="Fare",
                  payment_method_raw="Periodic Billing", expense_code="UNKNOWN",
                  request_date_utc="07/21/2026", request_time_utc="10:00:00 AM",
                  request_date_local="07/21/2026", request_time_local="10:00:00 AM",
                  dropoff_date_utc="07/21/2026", dropoff_time_utc="10:30:00 AM",
                  dropoff_date_local="07/21/2026", dropoff_time_local="07:30:00 AM",
                  email="alice@corp.example")
        tx_rows.append(bad)
        total = "20,001" if overprecision else "20,00"
    write_csv(input_dir, "transactions.csv", tx_rows)
    write_aux_csv(input_dir / "usuarios_internos.csv",
                  ["id_usuario", "nome_exibicao", "email_principal", "emails_alternativos", "matricula", "centro_custo", "status"],
                  [["U001", "Alice Example", "alice@corp.example", "", "0001", "CC001", "ATIVO"]])
    write_aux_xlsx(input_dir / "funcionarios.xlsx",
                   ["matricula", "nome", "cpf", "departamento", "centro_de_custo", "cargo", "data_admissao", "situacao", "data_desligamento"],
                   [["0001", "Alice Example", "52998224725", "D01", "CC001", "Analista", "01/01/2020", "Ativo", ""]],
                   sheet="Funcionarios")
    write_aux_xlsx(input_dir / "centros.xlsx", ["codigo", "descricao", "ativo", "responsavel"], [["CC001", "Administrativo", "Sim", "Gestor"]])
    write_aux_csv(input_dir / "cartoes.csv", ["bandeira", "final", "tipo", "titular"], [["AMERICAN_EXPRESS", "3008", "CREDITO_CORPORATIVO", "Empresa"]])
    write_aux_csv(input_dir / "expense.csv", ["codigo_despesa", "descricao", "conta_contabil", "conta_gerencial_sugerida", "observacao"],
                  [["GOOD", "Despesa válida", "5.1.01.001", "G3.02", ""]])
    write_aux_csv(input_dir / "accounts.csv", ["codigo", "descricao", "tipo", "natureza", "aceita_lancamento"],
                  [["5.1.01.001", "Despesa", "Despesa", "D", "S"]])
    write_aux_csv(input_dir / "crosswalk.csv", ["conta_contabil", "conta_gerencial", "descricao_contabil", "descricao_gerencial"],
                  [["5.1.01.001", "G3.02", "Despesa", "Despesa"]])
    write_aux_csv(input_dir / "managerial.csv", ["codigo_gerencial", "descricao", "grupo", "aceita_lancamento"],
                  [["G3.02", "Despesa", "Despesa", "S"]])
    write_aux_xlsx(input_dir / "vendors.xlsx",
                   ["Razão Social", "Nome Fantasia", "CNPJ", "Inscrição Estadual", "Município", "UF", "E-mail", "Telefone", "Condição de Pagamento"],
                   [["Uber do Brasil Tecnologia Ltda", "Uber", "28696184000195", "ISENTO", "Curitiba", "PR", "ap@uber.example", "", "Boleto"]])
    statement_headers = ["numero_demonstrativo", "cnpj_emitente", "periodo_inicio", "periodo_fim", "data_disponibilizacao", "data_vencimento", "forma_pagamento", "cobrancas_usuario", "taxas_servico", "valor_total", "observacao", "data_emissao"]
    write_aux_csv(input_dir / "demonstrativo.csv", statement_headers,
                  [["SYN-2026-07", "28.696.184/0001-95", "02/07/2026" if partial_period else "01/07/2026", "31/07/2026", "03/08/2026", "10/08/2026", "Boleto", total, "0,00", total, "fixture", "02/08/2026"]], delimiter=";")
    return input_dir


def check_stage3_synthetic(folder: Path):
    valid_input = make_stage3_fixture(folder / "valid", with_cards=True)
    valid_output = folder / "valid_output"
    call_pipeline(valid_input, valid_output)
    for erp_file in ("ap_titulos.csv", "ap_rateios.csv"):
        assert not (valid_output / erp_file).read_bytes().startswith(b"\xef\xbb\xbf"), f"{erp_file} must be UTF-8 without BOM"
    # Strict UTF-8: a BOM would surface as '﻿id_externo' and fail the header assertions below.
    title_rows = list(csv.DictReader((valid_output / "ap_titulos.csv").open(encoding="utf-8", newline="")))
    allocation_rows = list(csv.DictReader((valid_output / "ap_rateios.csv").open(encoding="utf-8", newline="")))
    assert list(title_rows[0]) == ["id_externo", "tipo", "beneficiario_tipo", "beneficiario_documento", "beneficiario_nome", "num_documento", "data_emissao", "data_vencimento", "competencia", "valor_total", "moeda", "historico", "origem"]
    assert list(allocation_rows[0]) == ["id_externo_titulo", "seq", "conta_contabil", "conta_gerencial", "centro_custo", "valor", "competencia", "historico"]
    by_type = {r["tipo"]: r for r in title_rows}
    assert len(title_rows) == 2 and by_type["FATURA_FORNECEDOR"]["valor_total"] == "10.00", title_rows
    reimbursement = by_type["REEMBOLSO_COLABORADOR"]
    assert (reimbursement["valor_total"], reimbursement["data_emissao"], reimbursement["data_vencimento"], reimbursement["beneficiario_documento"]) == ("7.50", "2026-07-31", "2026-08-15", "52998224725"), reimbursement
    assert len(allocation_rows) == 2 and {r["valor"] for r in allocation_rows} == {"10.00", "7.50"}, allocation_rows
    assert {r["centro_custo"] for r in allocation_rows} == {"CC001"}
    routes = dict(read_rows(valid_output / "canonical.duckdb", "select trip_id, payment_route_status from int_transaction_enrichment"))
    assert routes["ap-amex"] == "excluded_corporate_card_statement" and routes["ap-personal"] == "employee_reimbursement_candidate", routes
    assert "occurrence_ids" in (valid_output / "ap_rateios_linhagem.csv").read_text(encoding="utf-8-sig").splitlines()[0]
    payable_hashes = (file_hash(valid_output / "ap_titulos.csv"), file_hash(valid_output / "ap_rateios.csv"))
    call_pipeline(valid_input, valid_output)
    assert payable_hashes == (file_hash(valid_output / "ap_titulos.csv"), file_hash(valid_output / "ap_rateios.csv"))
    if os.name == "nt":
        # The published output inherits the parent's permissions instead of an owner-only ACL.
        acl = subprocess.run(["icacls", str(valid_output)], capture_output=True, text=True, errors="replace").stdout
        assert "(I)" in acl, acl

    # A failed build must preserve the previously published imports byte-for-byte.
    unknown_input = folder / "unknown" / "input"
    shutil.copytree(valid_input, unknown_input)
    (unknown_input / "unrecognized.csv").write_text("renamed_trip_id,amount\nX1,10.00\n", encoding="utf-8")
    failed = call_pipeline(unknown_input, valid_output, expect_ok=False)
    assert "unrecognized.csv" in failed.stderr and "RuntimeError" in failed.stderr
    assert payable_hashes == (file_hash(valid_output / "ap_titulos.csv"), file_hash(valid_output / "ap_rateios.csv"))
    assert not list(folder.glob(".valid_output.build-*")), "a failed build must not leave its temporary folder"

    cutover_output = folder / "cutover_output"
    call_pipeline(valid_input, cutover_output, as_of_date="2026-09-28", first_competence="2026-09")
    assert list(csv.DictReader((cutover_output / "ap_titulos.csv").open(encoding="utf-8", newline=""))) == []
    assert read_rows(cutover_output / "canonical.duckdb",
                     "select count(*) from int_ap_release_gate where list_contains(final_release_blockers,'competence_before_automation_start')") == [(2,)]

    ledger = folder / "issued_titles.csv"
    ledger.write_text("id_externo,valor_total,status,approved_at\n" +
                      f"{by_type['REEMBOLSO_COLABORADOR']['id_externo']},7.50,settled,2026-08-17\n", encoding="utf-8")
    issued_output = folder / "issued_output"
    call_pipeline(valid_input, issued_output, issued_ledger=ledger)
    assert read_rows(issued_output / "canonical.duckdb",
                     "select count(*) from int_ap_release_gate where list_contains(final_release_blockers,'title_already_issued_immutable')") == [(1,)]
    assert read_rows(issued_output / "canonical.duckdb",
                     "select adjustment_status from ap_ajustes_candidatos") == [("no_change",)]

    # Re-sent statement with different bytes but equal content: same ids, same releases, no double counting.
    historical_input = make_stage3_fixture(folder / 'historical_hr', with_cards=True)
    write_aux_xlsx(historical_input / 'funcionarios.xlsx',
                   ['matricula','nome','cpf','departamento','centro_de_custo','cargo','data_admissao','situacao','data_desligamento'],
                   [['0001','Alice Example','52998224725','D01','CC001','Analista','01/01/2020','Desligado','05/08/2026']], sheet='Funcionarios')
    write_aux_csv(historical_input / 'usuarios_internos.csv',
                  ['id_usuario','nome_exibicao','email_principal','emails_alternativos','matricula','centro_custo','status'],
                  [['U001','Alice Example','alice@corp.example','','0001','CC001','INATIVO']])
    historical_output = folder / 'historical_hr_output'
    call_pipeline(historical_input, historical_output)
    assert read_rows(historical_output / 'canonical.duckdb', 'select tipo from ap_titulos') == [('FATURA_FORNECEDOR',)]
    assert read_rows(historical_output / 'canonical.duckdb', "select count(*) from int_ap_release_gate where list_contains(final_release_blockers,'stage3_gate:former_employee_reimbursement_review')") == [(1,)]

    classification_input = make_stage3_fixture(folder / 'classification', with_cards=True)
    transaction_file = classification_input / 'transactions.csv'
    transaction_file.write_text(transaction_file.read_text(encoding='utf-8-sig').replace(',GOOD,', ',TRANSP-FUNC,'), encoding='utf-8-sig')
    write_aux_csv(classification_input / 'expense.csv',
                  ['codigo_despesa','descricao','conta_contabil','conta_gerencial_sugerida','observacao'],
                  [['TRANSP-FUNC','Revisão de classificação','5.1.01.001','G3.02','']])
    classification_output = folder / 'classification_output'
    call_pipeline(classification_input, classification_output)
    assert read_rows(classification_output / 'canonical.duckdb', 'select count(*) from ap_titulos') == [(0,)]
    assert read_rows(classification_output / 'canonical.duckdb', "select count(*) from int_ap_release_gate where list_contains(final_release_blockers,'cost_expense_classification_pending')") == [(2,)]

    resend_input = folder / "resend" / "input"
    shutil.copytree(valid_input, resend_input)
    (resend_input / "demonstrativo_reenvio.csv").write_bytes((valid_input / "demonstrativo.csv").read_bytes() + b"\r\n")
    resend_output = folder / "resend_output"
    call_pipeline(resend_input, resend_output)
    resend_titles = list(csv.DictReader((resend_output / "ap_titulos.csv").open(encoding="utf-8", newline="")))
    assert sorted(r["id_externo"] for r in resend_titles) == sorted(r["id_externo"] for r in title_rows), resend_titles
    assert read_rows(resend_output / "canonical.duckdb", "select statement_occurrence_count, statement_version_count from int_ap_title_candidates where tipo='FATURA_FORNECEDOR'") == [(2, 1)]

    # Two values under one statement number remain separate evidence, never a chosen payable amount.
    conflict_input = folder / "conflict" / "input"
    shutil.copytree(valid_input, conflict_input)
    original_statement = (valid_input / "demonstrativo.csv").read_bytes()
    assert original_statement.count(b"10,00") == 2
    (conflict_input / "demonstrativo_reenvio.csv").write_bytes(original_statement.replace(b"10,00", b"11,00"))
    conflict_output = folder / "conflict_output"
    call_pipeline(conflict_input, conflict_output)
    conflict = read_rows(conflict_output / "canonical.duckdb", "select statement_occurrence_count, statement_version_count, valor_total_candidato, statement_total, user_charges, service_fees, list_contains(final_release_blockers, 'statement_versions_conflict'), is_released from int_ap_release_gate where tipo='FATURA_FORNECEDOR'")
    assert conflict == [(2, 2, None, None, None, None, True, False)], conflict
    assert read_rows(conflict_output / "canonical.duckdb", "select count(*) from ap_titulos where tipo='FATURA_FORNECEDOR'") == [(0,)]
    conflict_summary = (conflict_output / "controller_summary.md").read_text(encoding="utf-8")
    assert all(x in conflict_summary for x in ("statement_versions_conflict", "valor devido indeterminado", "demonstrativo.csv", "demonstrativo_reenvio.csv", "R$ 10,00", "R$ 11,00")), conflict_summary
    assert "2026-07: demonstrativo R$ 10,00" not in conflict_summary

    blocked_input = make_stage3_fixture(folder / "blocked", include_bad_component=True)
    blocked_output = folder / "blocked_output"
    call_pipeline(blocked_input, blocked_output)
    blocked_titles = list(csv.DictReader((blocked_output / "ap_titulos_candidatos.csv").open(encoding="utf-8-sig", newline="")))
    assert len(blocked_titles) == 1 and blocked_titles[0]["is_released"] == "False", blocked_titles
    assert "periodic_billing_detail_has_blocked_component" in blocked_titles[0]["final_release_blockers"]
    assert list(csv.DictReader((blocked_output / "ap_titulos.csv").open(encoding="utf-8", newline=""))) == []
    assert list(csv.DictReader((blocked_output / "ap_rateios.csv").open(encoding="utf-8", newline=""))) == []
    assert len(list(csv.DictReader((blocked_output / "ap_rateios_candidatos.csv").open(encoding="utf-8-sig", newline="")))) >= 2

    precision_input = make_stage3_fixture(folder / "precision", overprecision=True, partial_period=True)
    precision_output = folder / "precision_output"
    call_pipeline(precision_input, precision_output)
    precision_issues = read_rows(precision_output / "canonical.duckdb", "select statement_total,total_text_valid,period_is_full_month from stg_uber_statements")
    assert precision_issues == [(None, False, False)], precision_issues
    precision_titles = list(csv.DictReader((precision_output / "ap_titulos_candidatos.csv").open(encoding="utf-8-sig", newline="")))
    assert precision_titles[0]["is_released"] == "False"
    assert "statement_amount_missing_invalid_or_over_precision" in precision_titles[0]["final_release_blockers"]
    assert "statement_period_not_a_complete_calendar_month" in precision_titles[0]["final_release_blockers"]


def main():
    if TEST_ROOT.exists():
        resolved = TEST_ROOT.resolve(strict=True)
        allowed = TEST_ROOT.parent.resolve(strict=True)
        if allowed not in resolved.parents or TEST_MARKER.read_text(encoding="utf-8") != "Stage 1 synthetic test output; safe to recreate.\n":
            raise RuntimeError(f"Refusing to clean unmarked synthetic directory: {resolved}")
        shutil.rmtree(TEST_ROOT)
    TEST_ROOT.mkdir(parents=True)
    TEST_MARKER.write_text("Stage 1 synthetic test output; safe to recreate.\n", encoding="utf-8")
    input_dir = TEST_ROOT / "input"
    a = [
        row("trip-dup", "20/08/26 12:00:00", amount="10.00", kind="Adjustment"),
        row("trip-dup", "20/08/26 12:00:00", amount="10.00", kind="Adjustment"),
        row("trip-null-zero", "20/08/26 12:01:00", amount="", kind="Adjustment"),
        row("trip-a15", "20/08/26 13:00:00", request="12:00:10 PM"),
        row("trip-fare", "20/08/26 14:01:00", kind="Fare", amount="2.00"),
        row("trip-fare", "20/08/26 14:02:00", kind="Fare", amount="3.00"),
        row("trip-bad-ts", "not-a-date", kind="Tip", amount="4.00"),
        row("trip-residual", "20/08/26 15:00:00", amount="66.93000000000001"),
        row("trip-money-error", "20/08/26 16:00:00", amount="10.000001"),
    ]
    b = [
        row("trip-dup", "20/08/26 12:00:00", amount="10.00", kind="Adjustment"),
        row("trip-null-zero", "20/08/26 12:01:00", amount="0.00", kind="Adjustment"),
        row("trip-a15", "20/08/26 13:00:00", request="12:00:50 PM"),
        row("trip-fare", "20/08/26 14:01:00", kind="Fare", amount="2.50"),
        row("trip-unknown", "20/08/26 17:00:00", kind="Mystery", amount="6.00"),
    ]
    c = [row("trip-a15", "20/08/26 13:00:00", request="12:00 PM")]
    write_csv(input_dir, "source_a.csv", a)
    write_csv(input_dir, "source_b.csv", b, reverse=True)
    write_csv(input_dir, "source_c.csv", c)
    shutil.copyfile(input_dir / "source_a.csv", input_dir / "source_a_identical.csv")

    out1 = TEST_ROOT / "run1"
    call_pipeline(input_dir, out1)
    db1 = out1 / "canonical.duckdb"
    counts = read_rows(db1, "select (select count(*) from raw_uber_occurrences),(select count(*) from stg_uber_transactions),(select count(*) from int_transaction_versions),(select count(*) from int_transactions)")[0]
    assert counts == (15, 15, 15, 9), counts
    assert read_rows(db1, "select count(*) from int_transaction_versions where key_status='within_file_duplicate'")[0][0] == 3
    assert read_rows(db1, "select count(*) from int_transaction_versions v join stg_uber_transactions s using(occurrence_id) where s.trip_id='trip-a15' and list_contains(v.conflict_fields,'request_ts_utc')")[0][0] == 3
    assert read_rows(db1, "select list_sort(list(second(request_ts_utc))) from stg_uber_transactions where trip_id='trip-a15'")[0][0] == [0, 10, 50]
    assert read_rows(db1, "select amount_status from int_transactions where trip_id='trip-null-zero'")[0][0] == "disputed"
    assert read_rows(db1, "select count(*) from int_transactions where trip_id='trip-fare' and fare_duplicate_trip and is_quarantined")[0][0] == 2
    assert read_rows(db1, "select retention_reasons from int_transactions where trip_id='trip-unknown'")[0][0] == ["unknown_transaction_type"]
    assert read_rows(db1, "select count(*) from int_transactions where business_key is null and list_contains(retention_reasons,'identity_unresolved')")[0][0] == 1
    assert read_rows(db1, "select card_last4,requester_email from stg_uber_transactions limit 1")[0] == ("0042", "comprador@example.com")
    assert read_rows(db1, "select amount_brl,parse_errors from stg_uber_transactions where trip_id='trip-residual'")[0][0] == Decimal("66.93")
    assert any("66.93000000000001->66.93" in x for x in read_rows(db1, "select technical_changes from stg_uber_transactions where trip_id='trip-residual'")[0][0])
    assert read_rows(db1, "select amount_brl,parse_errors from stg_uber_transactions where trip_id='trip-money-error'")[0][0] is None
    assert "amount_brl:parse_error" in read_rows(db1, "select parse_errors from stg_uber_transactions where trip_id='trip-money-error'")[0][0]
    manifest = json.loads((out1 / "input_manifest.json").read_text(encoding="utf-8"))
    assert next(x for x in manifest["unique_content"] if x["reference_file"] == "source_a.csv")["aliases"] == ["source_a.csv", "source_a_identical.csv"]

    fare_key, fare_ids = read_rows(db1, "select business_key,occurrence_ids from int_transactions where trip_id='trip-fare' and amount_status='disputed'")[0]
    if isinstance(fare_ids, str): fare_ids = json.loads(fare_ids)
    chosen = read_rows(db1, "select occurrence_id from raw_uber_occurrences where source_file='source_b.csv' and json_extract_string(canonical_values,'$.trip_id')='trip-fare'")[0][0]
    decision_rows = [make_decision(db1, "trip-null-zero", "reject_all"), [fare_key, json.dumps(sorted(fare_ids), separators=(",", ":")), "accept_occurrence", chosen, "synthetic_test", "2026-09-27T00:00:00Z", "accept full source occurrence"]]
    seed = TEST_ROOT / "resolutions.csv"
    save_seed(seed, decision_rows)
    out2 = TEST_ROOT / "run2"
    call_pipeline(input_dir, out2, seed)
    db2 = out2 / "canonical.duckdb"
    accepted = read_rows(db2, "select resolution_status,amount_brl,retention_reasons,fare_duplicate_trip from int_transactions where trip_id='trip-fare' and key_status='conflict'")[0]
    assert accepted[0] == "applied" and accepted[1] == Decimal("2.50") and accepted[2] == ["fare_duplicate_trip"] and accepted[3]
    rejected = read_rows(db2, "select resolution_status,retention_reasons from int_transactions where trip_id='trip-null-zero'")[0]
    assert rejected == ("applied", ["conflict", "rejected_by_decision"])
    repeat_hash = file_hash(out2 / "int_transactions.csv")
    call_pipeline(input_dir, out2, seed)
    assert file_hash(out2 / "int_transactions.csv") == repeat_hash

    write_csv(input_dir, "source_d.csv", [row("trip-null-zero", "20/08/26 12:01:00", amount="0.00", kind="Adjustment")])
    out3 = TEST_ROOT / "run3"
    call_pipeline(input_dir, out3, seed)
    stale = read_rows(out3 / "canonical.duckdb", "select resolution_status,retention_reasons from int_transactions where trip_id='trip-null-zero'")[0]
    assert stale == ("stale", ["conflict", "resolution_stale"]), stale

    d8 = TEST_ROOT / "d8_input"
    write_csv(d8, "collision.csv", [row("trip-collision", "20/08/26 18:00:00", amount="1.00"), row("trip-collision", "20/08/26 18:00:10", amount="1.00")])
    failed = call_pipeline(d8, TEST_ROOT / "d8_run", expect_ok=False)
    assert "no_minute_key_collision_with_seconds" in failed.stdout
    assert not list(TEST_ROOT.glob(".d8_run.build-*")), "a failed dbt build must not leave its temporary folder"
    call_pipeline(d8, TEST_ROOT / "d8_keep", expect_ok=False, extra_args=["--keep-failed-build"])
    kept = list(TEST_ROOT.glob(".d8_keep.build-*"))
    assert len(kept) == 1 and (kept[0] / "logs").is_dir(), kept
    shutil.rmtree(kept[0])
    check_stage3_synthetic(TEST_ROOT / "stage3")
    print("synthetic_checks=PASS; scenarios=column_reorder,byte_alias,within_file_repeat,null_vs_zero,A15,unknown_type,identity_error,multi_fare,accept,reject,stale,rereun,money_residual,money_threshold,D8,failed_build_cleanup,keep_failed_build,inherited_output_acl,AP_valid_release,AP_reimbursement_release,erp_utf8_no_bom,card_brand_case_route_by_type,statement_resend_same_ids,statement_conflict_unknown_total,AP_whole_title_blocked_by_component,statement_overprecision,partial_month_period")


if __name__ == "__main__":
    main()

