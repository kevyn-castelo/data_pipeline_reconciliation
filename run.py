from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
import zipfile
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path
from xml.etree import ElementTree as ET

import duckdb
import openpyxl


ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / "config/client.json").read_text(encoding="utf-8"))
CANONICAL_FIELDS = {
    "trip_id": ["Trip/Eats ID"], "transaction_ts_utc": ["Transaction Timestamp (UTC)", "Transaction timestamp (UTC)"],
    "request_date_utc": ["Request Date (UTC)", "Request date (UTC)"], "request_time_utc": ["Request Time (UTC)", "Request time (UTC)"],
    "request_date_local": ["Request Date (Local)", "Request date (Local)"], "request_time_local": ["Request Time (Local)", "Request time (Local)"],
    "dropoff_date_utc": ["Drop-off Date (UTC)", "Drop-off date (UTC)"], "dropoff_time_utc": ["Drop-off Time (UTC)", "Drop-off time (UTC)"],
    "dropoff_date_local": ["Drop-off Date (Local)", "Drop-off date (Local)"], "dropoff_time_local": ["Drop-off Time (Local)", "Drop-off time (Local)"],
    "request_utc_offset": ["Request Timezone Offset from UTC", "Request timezone offset from UTC"],
    "first_name": ["First Name", "First name"], "last_name": ["Last Name", "Surname"], "email": ["Email"], "uber_employee_id_raw": ["Employee ID"], "uber_group": ["Group"],
    "service": ["Service"], "program": ["Program", "Programme"], "city": ["City"], "country": ["Country"], "expense_code": ["Expense Code", "Expense code"],
    "expense_memo": ["Expense Memo", "Expense memo"], "payment_method_raw": ["Payment Method", "Payment method"], "transaction_type": ["Transaction Type", "Transaction type"],
    "amount_local": ["Transaction Amount (local currency)", "Transaction Amount"], "local_currency": ["Local Currency", "Local currency code"],
    "tips_brl": ["Tips in BRL", "Tip in BRL (Inclusive of taxes, if any)"], "total_fare_brl": ["Total Fare in BRL", "Totals Fare in BRL"],
    "employee_paid_brl": ["Payments made by employees/guests in BRL"], "amount_brl": ["Transaction Amount in BRL", "Transaction amount in BRL"],
    "uber_invoice_number": ["Invoice Number", "Uber Fare Invoice#"], "requester": ["Conditional Columns"],
}
IDENTITY_FIELDS = {"trip_id", "transaction_ts_utc", "transaction_type"}
ERP_IMPORT_TABLES = {"ap_titulos", "ap_rateios"}
MONEY_FIELDS = {"amount_brl", "total_fare_brl", "employee_paid_brl", "tips_brl", "amount_local"}
DATE_PARTS = {"request_date_utc", "request_date_local", "dropoff_date_utc", "dropoff_date_local"}
AUX_SPECS = {
    "internal_users": {
        "fields": {"user_id": ["id_usuario"], "display_name": ["nome_exibicao"], "primary_email": ["email_principal"],
                   "alternate_emails": ["emails_alternativos"], "employee_number": ["matricula"],
                   "directory_cost_center": ["centro_custo"], "status": ["status"]},
        "signature": {"idusuario", "emailprincipal", "matricula", "emailsalternativos"}},
    "employees": {
        "fields": {"employee_number": ["matricula"], "employee_name": ["nome"], "cpf_raw": ["cpf"],
                   "department_id": ["departamento"], "official_cost_center": ["centro_de_custo", "centro_custo"],
                   "role": ["cargo"], "admission_date": ["data_admissao"], "status": ["situacao"],
                   "termination_date": ["data_desligamento"]},
        "signature": {"matricula", "cpf", "centrodecusto", "situacao"}},
    "cost_centers": {
        "fields": {"cost_center": ["codigo"], "description": ["descricao"], "active_flag": ["ativo"], "manager": ["responsavel"]},
        "signature": {"codigo", "descricao", "ativo", "responsavel"}},
    "corporate_cards": {
        "fields": {"card_brand": ["bandeira"], "card_last4": ["final"], "card_type": ["tipo"],
                   "cardholder": ["titular"], "issuer": ["banco_emissor"], "observation": ["observacao"]},
        "signature": {"bandeira", "final", "tipo", "titular"}},
    "expense_code_map": {
        "fields": {"expense_code": ["codigo_despesa"], "description": ["descricao"],
                   "accounting_target_account": ["conta_contabil"],
                   "managerial_suggested_account": ["conta_gerencial_sugerida"], "observation": ["observacao"]},
        "signature": {"codigodespesa", "contacontabil", "contagerencialsugerida"}},
    "accounting_accounts": {
        "fields": {"account_code": ["codigo"], "description": ["descricao"], "account_type": ["tipo"],
                   "nature": ["natureza"], "accepts_posting": ["aceita_lancamento"]},
        "signature": {"codigo", "descricao", "aceitalancamento"}},
    "accounting_managerial_map": {
        "fields": {"accounting_account": ["conta_contabil"], "managerial_account": ["conta_gerencial"],
                   "accounting_description": ["descricao_contabil"], "managerial_description": ["descricao_gerencial"]},
        "signature": {"contacontabil", "contagerencial", "descricaocontabil"}},
    "managerial_accounts": {
        "fields": {"managerial_account": ["codigo_gerencial"], "description": ["descricao"], "account_group": ["grupo"],
                   "accepts_posting": ["aceita_lancamento"]},
        "signature": {"codigogerencial", "descricao", "aceitalancamento"}},
    "vendors": {
        "fields": {"legal_name": ["razao_social"], "trade_name": ["nome_fantasia"], "cnpj_raw": ["cnpj"],
                   "state_registration": ["inscricao_estadual"], "city": ["municipio"], "state": ["uf"],
                   "email": ["email"], "phone": ["telefone"], "payment_terms": ["condicao_de_pagamento"]},
        "signature": {"razaosocial", "cnpj", "nomefantasia"}},
    "statements": {
        "fields": {"statement_number": ["numero_demonstrativo"], "issuer_cnpj_raw": ["cnpj_emitente"],
                   "period_start_raw": ["periodo_inicio"], "period_end_raw": ["periodo_fim"],
                   "availability_date_raw": ["data_disponibilizacao"], "explicit_issue_date_raw": ["data_emissao"],
                   "due_date_raw": ["data_vencimento"],
                   "payment_method": ["forma_pagamento"], "user_charges_raw": ["cobrancas_usuario"],
                   "service_fees_raw": ["taxas_servico"], "total_raw": ["valor_total"],
                   "observation": ["observacao"]},
        "signature": {"numerodemonstrativo", "cnpjemitente", "periodoinicio", "periodofim", "datavencimento", "valortotal"}},
}


def clean(v):
    if v is None:
        return None
    if isinstance(v, (datetime, date, time)):
        return v.isoformat(sep=" ") if isinstance(v, datetime) else v.isoformat()
    return str(v)


def clean_identifier(v):
    if v is None:
        return None
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


def brazilian_document_digits(value):
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def valid_cpf(value):
    d = brazilian_document_digits(value)
    if len(d) != 11 or len(set(d)) == 1:
        return False
    for size in (9, 10):
        total = sum(int(d[i]) * (size + 1 - i) for i in range(size))
        check = 11 - total % 11
        if check > 9:
            check = 0
        if int(d[size]) != check:
            return False
    return True


def valid_cnpj(value):
    d = brazilian_document_digits(value)
    if len(d) != 14 or len(set(d)) == 1:
        return False
    weights = ([5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2], [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    for size, row in zip((12, 13), weights):
        total = sum(int(d[i]) * row[i] for i in range(size))
        check = 11 - total % 11
        if int(d[size]) != (0 if check > 9 else check):
            return False
    return True


def digest(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def code_digest():
    """Hash the executable rules and configuration, including file names and bytes."""
    paths = [ROOT / "run.py", ROOT / "bank_reconciliation.py", ROOT / "requirements.txt", ROOT / "config/client.json", ROOT / "config/reconciliation.json"]
    # Only versioned rules: dbt's telemetry id (.user.yml, a per-machine UUID) and artifacts of manual
    # dbt runs (target/, logs/, dbt_packages/) would make the hash differ for identical code.
    generated = {"target", "logs", "dbt_packages"}
    paths.extend(sorted(p for pattern in ("*.sql", "*.yml") for p in (ROOT / "dbt").rglob(pattern)
                        if not p.name.startswith(".") and not generated & set(p.relative_to(ROOT / "dbt").parts)))
    h = hashlib.sha256()
    for path in paths:
        h.update(path.relative_to(ROOT).as_posix().encode("utf-8"))
        h.update(b"\0")
        h.update(path.read_bytes())
        h.update(b"\0")
    return h.hexdigest()


def dbt_cli_for_python(python_executable: str | Path, platform_name: str | None = None) -> Path:
    """Use the dbt command installed in the same virtual environment as Python."""
    return Path(python_executable).with_name("dbt.exe" if (platform_name or os.name) == "nt" else "dbt")


def load_issued_ledger(con, path):
    con.execute("CREATE TABLE raw_issued_titles(id_externo VARCHAR PRIMARY KEY, valor_total DECIMAL(15,2), status VARCHAR, approved_at DATE)")
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ["id_externo", "valor_total", "status", "approved_at"]:
            raise ValueError("Livro de títulos emitidos deve ter id_externo,valor_total,status,approved_at")
        seen = set()
        for row in reader:
            title_id = row["id_externo"].strip()
            if not title_id or title_id in seen:
                raise ValueError(f"ID vazio/duplicado no livro de títulos emitidos: {title_id!r}")
            seen.add(title_id)
            value = Decimal(row["valor_total"])
            if value <= 0 or value.as_tuple().exponent < -2:
                raise ValueError(f"Valor inválido no livro de títulos emitidos: {title_id}")
            status = row["status"].strip().lower()
            if status not in {"issued", "settled", "cancelled"}:
                raise ValueError(f"Status inválido no livro de títulos emitidos: {title_id}")
            approved_at = date.fromisoformat(row["approved_at"])
            con.execute("INSERT INTO raw_issued_titles VALUES (?,?,?,?)", [title_id, value, status, approved_at])


def norm_header(v):
    import unicodedata
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", str(v or "")).encode("ascii", "ignore").decode().lower())


def field_mapping(headers):
    normalized = {}
    for i, h in enumerate(headers):
        normalized.setdefault(norm_header(h), []).append(i)
    result = {}
    for field, aliases in CANONICAL_FIELDS.items():
        matches = sorted({i for a in aliases for i in normalized.get(norm_header(a), [])})
        if len(matches) > 1:
            raise ValueError(f"Cabeçalho ambíguo para {field}: {[headers[i] for i in matches]}")
        if matches:
            result[field] = matches[0]
    required = {"trip_id", "transaction_ts_utc", "transaction_type", "amount_brl"}
    if not required <= result.keys():
        raise ValueError(f"Layout Uber desconhecido; campos ausentes: {sorted(required - result.keys())}")
    return result


def read_csv(path):
    data = path.read_bytes()
    encoding = next((e for e in ("utf-8-sig", "cp1252") if _decodes(data, e)), None)
    if not encoding:
        raise ValueError(f"Codificação CSV não suportada: {path.name}")
    text = data.decode(encoding)
    initial = text.splitlines()[:12]
    delimiter = ";" if sum(line.count(";") for line in initial) > sum(line.count(",") for line in initial) else ","
    rows = list(csv.reader(text.splitlines(keepends=True), delimiter=delimiter))
    header_idx = next((i for i, r in enumerate(rows) if any(norm_header(c) == norm_header("Trip/Eats ID") for c in r)), None)
    if header_idx is None:
        return None
    header = rows[header_idx]
    mapping = field_mapping(header)
    # Reparse with newline-aware csv.reader so quoted multiline records keep their logical and physical positions.
    reader = csv.reader(text.splitlines(keepends=True), delimiter=delimiter)
    records, start, found_header, ignored = [], 1, False, 0
    for logical_row, row in enumerate(reader, start=1):
        end = reader.line_num
        if not found_header:
            if row == header:
                found_header = True
                start = end + 1
            continue
        if not row or not any(str(v).strip() for v in row):
            ignored += 1
            start = end + 1
            continue
        if _is_conditional_columns_footnote(row):
            ignored += 1
            start = end + 1
            continue
        records.append((row, start, end, logical_row))
        start = end + 1
    metadata = {"encoding": encoding, "delimiter": delimiter, "header_row": header_idx + 1,
                "company_header_raw": _preamble_value(rows[:header_idx], "company:"),
                "report_date_raw": _preamble_value(rows[:header_idx], "report date:"), "mapping": mapping, "n_ignored": ignored}
    return header, records, metadata


def _decodes(data, enc):
    try:
        data.decode(enc)
        return True
    except UnicodeDecodeError:
        return False


def _preamble_value(rows, key):
    for row in rows:
        if row and str(row[0]).strip().casefold() == key:
            return row[1] if len(row) > 1 else None
    return None


def _is_conditional_columns_footnote(values):
    populated = [str(v or "").strip() for v in values if str(v or "").strip()]
    return len(populated) == 1 and populated[0].casefold().startswith("*conditional columns are the columns that are applicable")


def _xlsx_raw_cells(path):
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main", "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships", "p": "http://schemas.openxmlformats.org/package/2006/relationships"}
    with zipfile.ZipFile(path) as z:
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        rel = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        targets = {x.attrib["Id"]: x.attrib["Target"] for x in rel}
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            shared = ["".join(t.text or "" for t in si.findall(".//m:t", ns)) for si in root.findall("m:si", ns)]
        sheets = {}
        for sh in wb.findall("m:sheets/m:sheet", ns):
            target = targets[sh.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]]
            target = target.lstrip("/") if target.startswith("/") else "xl/" + target
            root = ET.fromstring(z.read(target))
            cells = {}
            for c in root.findall(".//m:sheetData/m:row/m:c", ns):
                v = c.find("m:v", ns)
                if v is None:
                    inline = c.find("m:is", ns)
                    cells[c.attrib["r"]] = "".join(t.text or "" for t in inline.findall(".//m:t", ns)) if inline is not None else None
                elif c.attrib.get("t") == "s":
                    cells[c.attrib["r"]] = shared[int(v.text)]
                else:
                    cells[c.attrib["r"]] = v.text
            sheets[sh.attrib["name"]] = cells
    workbook_pr = wb.find("m:workbookPr", ns)
    return sheets, workbook_pr is not None and workbook_pr.attrib.get("date1904", "0") in {"1", "true", "True"}


def read_xlsx(path):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    raw_sheets, date1904 = _xlsx_raw_cells(path)
    result = []
    for ws in wb.worksheets:
        values = list(ws.iter_rows(values_only=True))
        header_idx = next((i for i, r in enumerate(values) if any(norm_header(c) == norm_header("Trip/Eats ID") for c in r if c is not None)), None)
        if header_idx is None:
            result.append({"sheet": ws.title, "role": "ignored_non_transactional", "n_ignored": ws.max_row, "n_records": 0})
            continue
        headers = [clean(x) for x in values[header_idx]]
        mapping = field_mapping(headers)
        records, ignored = [], 0
        for rn in range(header_idx + 1, len(values)):
            row = values[rn]
            if not any(v is not None for v in row):
                ignored += 1
                continue
            if _is_conditional_columns_footnote(row):
                ignored += 1
                continue
            vals = {}
            for h, i in zip(headers, range(len(headers))):
                col = openpyxl.utils.get_column_letter(i + 1)
                vals[h] = raw_sheets[ws.title].get(f"{col}{rn+1}")
            records.append((vals, rn + 1))
        pre = values[:header_idx]
        company = next((r[1] for r in pre if r and str(r[0]).strip().casefold() == "company:" and len(r) > 1), None)
        report = next((clean(r[1]) for r in pre if r and str(r[0]).strip().casefold() == "report date:" and len(r) > 1), None)
        result.append({"sheet": ws.title, "role": "transactions", "headers": headers, "mapping": mapping, "records": records,
                       "company": clean(company), "report_date": report, "header_row": header_idx + 1, "n_ignored": ignored, "date1904": date1904,
                       "epoch": "1904-01-01" if date1904 else "1899-12-30"})
    return result


def canonical_row(raw_map, mapping, headers):
    return {field: raw_map.get(headers[index]) for field, index in mapping.items()}


def identify_sources(source_dir):
    found, by_hash = [], {}
    for p in sorted(Path(source_dir).iterdir(), key=lambda x: x.name.casefold()):
        if p.suffix.lower() not in {".csv", ".xlsx"}:
            continue
        sha = digest(p)
        if sha in by_hash:
            by_hash[sha].append(p.name)
            continue
        by_hash[sha] = [p.name]
        found.append((p, sha))
    return found, by_hash


def _aux_entity(headers):
    normalized = {norm_header(h) for h in headers if h is not None}
    matches = [entity for entity, spec in AUX_SPECS.items() if spec["signature"] <= normalized]
    if len(matches) > 1:
        raise ValueError(f"Cabeçalhos auxiliares ambíguos: {matches}")
    return matches[0] if matches else None


def _explicit_nontransactional_csv(path):
    data = path.read_bytes()
    encoding = next((e for e in ("utf-8-sig", "cp1252") if _decodes(data, e)), None)
    if encoding is None:
        return False
    for line in data.decode(encoding).splitlines()[:15]:
        cells = {norm_header(x) for x in re.split(r"[;\t]", line)}
        if {"data", "lancamento", "valorr", "saldor"} <= cells:
            return True
        if {"codigo", "nome", "centrocustovinculado"} <= cells:
            return True
    return False


def _aux_record(entity, headers, values):
    spec = AUX_SPECS[entity]
    index_by_name = {}
    for i, header in enumerate(headers):
        index_by_name.setdefault(norm_header(header), []).append(i)
    record = {}
    for target, aliases in spec["fields"].items():
        indices = sorted({i for alias in aliases for i in index_by_name.get(norm_header(alias), [])})
        if len(indices) > 1:
            raise ValueError(f"Coluna auxiliar ambígua {entity}.{target}: {[headers[i] for i in indices]}")
        value = values[indices[0]] if indices and indices[0] < len(values) else None
        record[target] = clean_identifier(value) if target in {"employee_number", "directory_cost_center", "official_cost_center", "cost_center", "card_last4", "account_code", "accounting_account", "managerial_account", "expense_code", "cnpj_raw", "issuer_cnpj_raw", "cpf_raw", "user_id", "card_brand", "legal_name"} else clean(value)
    return record


def _read_aux_candidates(source_dir):
    result = {entity: [] for entity in AUX_SPECS}
    found, _ = identify_sources(source_dir)
    by_sheet = set()
    for path, sha in found:
        if path.suffix.lower() == ".csv":
            data = path.read_bytes()
            encoding = next((e for e in ("utf-8-sig", "cp1252") if _decodes(data, e)), None)
            if not encoding:
                continue
            sample = data.decode(encoding)[:12000]
            delimiter = max((",", ";", "\t"), key=lambda d: sample.count(d))
            reader = csv.reader(data.decode(encoding).splitlines(keepends=True), delimiter=delimiter)
            headers = next(reader, None)
            if not headers:
                continue
            entity = _aux_entity(headers)
            if not entity:
                continue
            rownum, line_start = 1, reader.line_num + 1
            for values in reader:
                line_end = reader.line_num
                if not values or not any(str(v).strip() for v in values):
                    line_start = line_end + 1
                    continue
                rownum += 1
                record = _aux_record(entity, headers, values)
                result[entity].append((sha, path.name, None, rownum, line_start, line_end, record, {str(k): clean(v) for k, v in zip(headers, values)}))
                line_start = line_end + 1
            by_sheet.add((path.name, None))
        else:
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
            for ws in wb.worksheets:
                iterator = ws.iter_rows(values_only=True)
                headers = next(iterator, None)
                if not headers:
                    continue
                entity = _aux_entity(headers)
                if not entity:
                    continue
                for rownum, values in enumerate(iterator, start=2):
                    if not values or not any(v is not None and str(v).strip() for v in values):
                        continue
                    record = _aux_record(entity, headers, values)
                    original = {str(k): clean(v) for k, v in zip(headers, values) if k is not None}
                    result[entity].append((sha, path.name, ws.title, rownum, None, None, record, original))
                by_sheet.add((path.name, ws.title))
            wb.close()
    return result, by_sheet


def _insert_auxiliary_data(source_dir, con, raw_files):
    aux_rows, _source_sheets = _read_aux_candidates(source_dir)
    table_fields = {entity: list(spec["fields"]) for entity, spec in AUX_SPECS.items()}
    inventory = []
    for entity, rows in aux_rows.items():
        extra = []
        for sha, filename, sheet, rownum, line_start, line_end, values, original in rows:
            if entity == "employees":
                values["cpf_digits"] = brazilian_document_digits(values.get("cpf_raw")) or None
                values["cpf_valid"] = valid_cpf(values.get("cpf_raw"))
            elif entity == "vendors":
                values["cnpj_digits"] = brazilian_document_digits(values.get("cnpj_raw")) or None
                values["cnpj_valid"] = valid_cnpj(values.get("cnpj_raw"))
            extra.append((sha, filename, sheet, rownum, line_start, line_end, values, original))
        con.execute(f"CREATE TABLE raw_ref_{entity}(file_sha256 VARCHAR, source_file VARCHAR, source_sheet VARCHAR, source_row INTEGER, source_line_start INTEGER, source_line_end INTEGER, " + ", ".join(f"{f} VARCHAR" for f in table_fields[entity]) + (", cpf_digits VARCHAR, cpf_valid BOOLEAN" if entity == "employees" else ", cnpj_digits VARCHAR, cnpj_valid BOOLEAN" if entity == "vendors" else "") + ", original_values JSON)")
        columns = ["file_sha256", "source_file", "source_sheet", "source_row", "source_line_start", "source_line_end", *table_fields[entity]]
        if entity == "employees": columns += ["cpf_digits", "cpf_valid"]
        if entity == "vendors": columns += ["cnpj_digits", "cnpj_valid"]
        columns += ["original_values"]
        placeholders = ", ".join("?" for _ in columns)
        insert_rows = []
        for sha, filename, sheet, rownum, line_start, line_end, values, original in extra:
            insert_rows.append((sha, filename, sheet, rownum, line_start, line_end, *(values.get(k) for k in table_fields[entity]), *([values["cpf_digits"], values["cpf_valid"]] if entity == "employees" else [values["cnpj_digits"], values["cnpj_valid"]] if entity == "vendors" else []), json.dumps(original, ensure_ascii=False)))
        if insert_rows:
            con.executemany(f"INSERT INTO raw_ref_{entity} VALUES ({placeholders})", insert_rows)
        source_count = len({r[0] for r in rows})
        inventory.append((entity, source_count > 0, source_count, len(rows)))
    con.execute("CREATE TABLE raw_reference_inventory(entity_name VARCHAR PRIMARY KEY, source_present BOOLEAN, source_count INTEGER, record_count INTEGER)")
    con.executemany("INSERT INTO raw_reference_inventory VALUES (?, ?, ?, ?)", inventory)


def ingest(source_dir, con, outdir):
    files, aliases = identify_sources(source_dir)
    _, auxiliary_sheets = _read_aux_candidates(source_dir)
    raw_files, occurrences, layout_rows, errors = [], [], [], []
    for path, sha in files:
        try:
            if path.suffix.lower() == ".csv":
                parsed = read_csv(path)
                if parsed is None:
                    if (path.name, None) not in auxiliary_sheets and not _explicit_nontransactional_csv(path):
                        raise ValueError("Arquivo CSV não reconhecido: falta layout Uber ou cadastro/arquivo ignorado por assinatura explícita")
                    raw_files.append((sha, path.name, None, "csv", None, None, None, None, None, 0, 0, "ignored_non_transactional", None, None, "{}"))
                    continue
                headers, records, meta = parsed
                layout = _layout_id(headers)
                layout_rows.append((layout, json.dumps({field: headers[index] for field, index in meta["mapping"].items()}, ensure_ascii=False), json.dumps(sorted(meta["mapping"]))))
                vals = []
                for row, start, end, logical_row in records:
                    original = {h: clean(row[i]) if i < len(row) else None for i, h in enumerate(headers)}
                    canonical = canonical_row(original, meta["mapping"], headers)
                    vals.append((original, canonical, None, logical_row, start, end))
                date_formats = infer_date_formats(vals, headers, meta["mapping"], sha)
                decimal_separator = infer_decimal_separator(vals, headers, meta["mapping"])
                parse_config = json.dumps({"date_formats": date_formats, "decimal_separator": decimal_separator}, sort_keys=True)
                raw_files.append((sha, path.name, None, "csv", meta["encoding"], meta["delimiter"], layout, meta["company_header_raw"], meta["header_row"], len(vals), meta["n_ignored"], "transactions", meta["report_date_raw"], "1899-12-30", parse_config))
                if meta["company_header_raw"] != CONFIG["expected_company_header"]:
                    raise ValueError(f"Company ausente/divergente em fonte transacional: {meta['company_header_raw']!r}")
                for original, canonical, sheet, rownum, start, end in vals:
                    occurrences.append((sha, path.name, None, _layout_id(headers), rownum, start, end, json.dumps(original, ensure_ascii=False), json.dumps(canonical, ensure_ascii=False), None))
            else:
                for sh in read_xlsx(path):
                    if sh["role"] != "transactions":
                        if (path.name, sh["sheet"]) not in auxiliary_sheets and sh["sheet"].casefold() != "resumo":
                            raise ValueError(f"Aba XLSX não reconhecida: {sh['sheet']}")
                        raw_files.append((sha, path.name, sh["sheet"], "xlsx", None, None, None, None, None, 0, sh["n_ignored"], sh["role"], None, "1899-12-30", "{}"))
                        continue
                    headers, mapping = sh["headers"], sh["mapping"]
                    layout = _layout_id(headers)
                    layout_rows.append((layout, json.dumps({field: headers[index] for field, index in mapping.items()}, ensure_ascii=False), json.dumps(sorted(mapping))))
                    if sh["company"] != CONFIG["expected_company_header"]:
                        raise ValueError(f"Company ausente/divergente em {sh['sheet']}: {sh['company']!r}")
                    date_formats = {}
                    vals = []
                    for record, rownum in sh["records"]:
                        canonical = canonical_row(record, mapping, headers)
                        vals.append((record, canonical, rownum))
                    raw_files.append((sha, path.name, sh["sheet"], "xlsx", None, None, layout, sh["company"], sh["header_row"], len(vals), sh["n_ignored"], "transactions", sh["report_date"], sh["epoch"], json.dumps(date_formats, sort_keys=True)))
                    for original, canonical, rownum in vals:
                        occurrences.append((sha, path.name, sh["sheet"], _layout_id(headers), rownum, None, None,
                                           json.dumps(original, ensure_ascii=False), json.dumps(canonical, ensure_ascii=False), None))
        except Exception as exc:
            errors.append({"file": path.name, "error": f"{type(exc).__name__}: {exc}"})
    if errors:
        raise RuntimeError(json.dumps(errors, ensure_ascii=False))
    _insert_auxiliary_data(source_dir, con, raw_files)
    con.execute("CREATE TABLE raw_files(file_sha256 VARCHAR, source_file VARCHAR, source_sheet VARCHAR, file_format VARCHAR, encoding VARCHAR, delimiter VARCHAR, layout_id VARCHAR, company_header_raw VARCHAR, header_row INTEGER, n_data_records INTEGER, n_ignored_records INTEGER, sheet_role VARCHAR, report_date_raw VARCHAR, workbook_epoch VARCHAR, date_formats_json JSON)")
    con.execute("CREATE TABLE raw_uber_occurrences(file_sha256 VARCHAR, source_file VARCHAR, source_sheet VARCHAR, layout_id VARCHAR, source_row INTEGER, source_line_start INTEGER, source_line_end INTEGER, original_values JSON, canonical_values JSON, occurrence_id VARCHAR)")
    con.execute("CREATE TABLE raw_layouts(layout_id VARCHAR PRIMARY KEY, field_mapping_json JSON, field_availability_json JSON)")
    con.executemany("INSERT INTO raw_files VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", raw_files)
    for layout, mapping_json, availability_json in sorted(set(layout_rows)):
        con.execute("INSERT INTO raw_layouts VALUES (?, ?::JSON, ?::JSON)", [layout, mapping_json, availability_json])
    for o in occurrences:
        sha, name, sheet, layout, row, lstart, lend, orig, canon, _ = o
        occid = f"{sha[:16]}:{sheet or ''}:{row}"
        con.execute("INSERT INTO raw_uber_occurrences VALUES (?, ?, ?, ?, ?, ?, ?, ?::JSON, ?::JSON, ?)", [sha, name, sheet, layout, row, lstart, lend, orig, canon, occid])
    (outdir / "input_manifest.json").write_text(json.dumps({"unique_content": [{"file_sha256": h, "reference_file": p.name, "aliases": aliases[h]} for (p, h) in files]}, ensure_ascii=False, indent=2), encoding="utf-8", newline="\r\n")


def _layout_id(headers):
    field_mapping(headers)
    signature = hashlib.sha256("|".join(sorted(norm_header(x) for x in headers)).encode()).hexdigest()[:10]
    return f"uber_{signature}"


def infer_date_formats(vals, headers, mapping, sha):
    result = {}
    overrides = CONFIG.get("date_format_overrides", {}).get(sha, {})
    for field in ("transaction_ts_utc", *DATE_PARTS):
        if field not in mapping:
            continue
        samples = [canonical[field] for _, canonical, *_ in vals if canonical.get(field)]
        samples = [x for x in samples if not re.fullmatch(r"\d+(?:\.\d+)?", str(x))]
        if not samples:
            continue
        ts = field == "transaction_ts_utc"
        patterns = (["%d/%m/%y %H:%M", "%m/%d/%y %H:%M", "%d/%m/%Y %H:%M", "%m/%d/%Y %H:%M",
                     "%d/%m/%y %H:%M:%S", "%m/%d/%y %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%m/%d/%Y %H:%M:%S",
                     "%d/%m/%y %H:%M:%S.%f", "%m/%d/%y %H:%M:%S.%f", "%d/%m/%Y %H:%M:%S.%f", "%m/%d/%Y %H:%M:%S.%f"]
                    if ts else ["%d/%m/%Y", "%m/%d/%Y", "%d/%m/%y", "%m/%d/%y"])
        proofs = set()
        for sample in samples:
            valid = []
            for fmt in patterns:
                try:
                    datetime.strptime(str(sample).strip(), fmt)
                    valid.append(fmt)
                except ValueError:
                    pass
            orders = {"DM" if fmt.startswith("%d/") else "MD" for fmt in valid}
            if len(orders) > 1:
                continue
            if orders:
                proofs.update(orders)
        if len(proofs) > 1:
            raise ValueError(f"Valores contraditórios DD/MM e MM/DD na coluna {field}")
        proof_order = next(iter(proofs), None)
        candidates = [fmt for fmt in patterns if ("DM" if fmt.startswith("%d/") else "MD") == proof_order] if proof_order else []
        if candidates:
            scored = [(sum(_format_accepts_sample(fmt, sample) for sample in samples), fmt) for fmt in candidates]
            score, fmt = max(scored)
            if score:
                result[field] = fmt
                continue
        override = overrides.get(field)
        if override in patterns:
            result[field] = override
        elif proof_order is None:
            raise ValueError(f"Data ambígua sem prova/override explícito: {sha} + {field}")
        else:
            raise ValueError(f"Não foi possível selecionar o formato comprovado para {field}")
    for field in ("request_date_utc", "request_date_local", "dropoff_date_utc", "dropoff_date_local"):
        if field in result:
            time_field = field.replace("date", "time")
            time_samples = [str(canonical.get(time_field)).strip() for _, canonical, *_ in vals if canonical.get(time_field)]
            if any(re.search(r"[AP]M", value, re.I) for value in time_samples):
                time_patterns = ["%I:%M:%S.%f %p", "%I:%M:%S %p", "%I:%M %p"]
            else:
                time_patterns = ["%H:%M:%S.%f", "%H:%M:%S", "%H:%M"]
            selected = next((fmt for fmt in time_patterns if any(_format_accepts_sample(fmt, value) for value in time_samples)), None)
            if selected is None:
                raise ValueError(f"Não foi possível inferir formato de horário para {time_field}")
            # Check every non-empty value against the selected shape. Invalid row values
            # remain in RAW and become parse_error in STAGING; the format is still proven.
            if not any(_format_accepts_sample(selected, value) for value in time_samples):
                raise ValueError(f"Formato de horário sem evidência para {time_field}")
            time_fmt = selected
            result[field.replace("date", "datetime")] = result[field] + " " + time_fmt
    return result


def infer_decimal_separator(vals, headers, mapping):
    seen = set()
    for _, canonical, *_ in vals:
        for field in MONEY_FIELDS:
            if field not in mapping:
                continue
            val = canonical.get(field)
            if val is None:
                continue
            s = str(val).strip()
            if re.fullmatch(r"[+-]?\d+,\d{2}", s): seen.add(",")
            if re.fullmatch(r"[+-]?\d+\.\d{2}", s): seen.add(".")
    if len(seen) > 1:
        raise ValueError(f"Separadores decimais contraditórios no mesmo arquivo: {sorted(seen)}")
    return next(iter(seen), None)


def _format_accepts_sample(fmt, sample):
    try:
        datetime.strptime(str(sample).strip(), fmt)
        return True
    except ValueError:
        return False


def main():
    ap = argparse.ArgumentParser(description="Pipeline auditável Uber → AP em RAW/STAGING/CANONICAL e dbt")
    ap.add_argument("--input", type=Path, default=ROOT / "data")
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--resolutions", type=Path, default=ROOT / "dbt/seeds/resolutions.csv")
    ap.add_argument("--issued-ledger", type=Path, default=ROOT / "config/issued_titles.csv")
    ap.add_argument("--as-of-date", type=date.fromisoformat, default=date.today(),
                    help="Data de corte YYYY-MM-DD para bloquear títulos vencidos; informe explicitamente em reruns auditáveis")
    ap.add_argument("--first-competence", default=CONFIG.get("first_automated_competence"),
                    help="Primeira competência YYYY-MM permitida para automação")
    ap.add_argument("--keep-failed-build", action="store_true",
                    help="Preserva a pasta temporária de um build com falha, para diagnóstico")
    args = ap.parse_args()
    if not args.first_competence or not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", args.first_competence):
        raise SystemExit("Primeira competência automatizada deve ser YYYY-MM válido.")
    if args.output.is_symlink():
        raise SystemExit("A saída não pode ser um link simbólico.")
    target_out = args.output.resolve()
    forbidden = {"data", "docs", "profiling", ".venv"}
    if target_out == ROOT or ROOT not in target_out.parents or any(x.casefold() in forbidden for x in target_out.parts) or target_out == args.input.resolve():
        raise SystemExit("A saída deve ser uma pasta dedicada dentro do workspace, fora de data/docs/profiling/.venv.")
    if target_out.exists() and not (target_out / ".uber_pipeline_output").is_file():
        raise SystemExit(f"A saída já existe sem marker do pipeline; nenhum arquivo será removido: {target_out}")
    if not args.resolutions.is_file():
        raise SystemExit(f"Seed de resolução não encontrado: {args.resolutions}")
    if not args.issued_ledger.is_file():
        raise SystemExit(f"Livro de títulos emitidos não encontrado: {args.issued_ledger}")
    target_out.parent.mkdir(parents=True, exist_ok=True)
    # A plain sibling folder inherits the parent's permissions. tempfile.mkdtemp restricts access to the
    # owner on Windows (Python >= 3.13), and the restriction would survive the rename into the output.
    out = target_out.with_name(f".{target_out.name}.build-{uuid.uuid4().hex[:12]}")
    out.mkdir()
    try:
        build_output(args, out)
        publish_output(out, target_out)
    except BaseException:
        if not out.exists():
            raise  # already published; the failure happened while removing the previous output
        if args.keep_failed_build:
            print(f"Build com falha preservado para diagnóstico: {out}", file=sys.stderr)
        else:
            shutil.rmtree(out, ignore_errors=True)
            print("Build com falha; pasta temporária removida (use --keep-failed-build para preservá-la). "
                  "A saída publicada anterior não foi alterada.", file=sys.stderr)
        raise


def build_output(args, out):
    (out / ".uber_pipeline_output").write_text("Pasta gerada por run.py.\n", encoding="utf-8", newline="\r\n")
    db = out / "canonical.duckdb"
    con = duckdb.connect(str(db))
    try:
        ingest(args.input, con, out)
        load_issued_ledger(con, args.issued_ledger)
    finally:
        con.close()
    dbt_cli = dbt_cli_for_python(sys.executable)
    if not dbt_cli.is_file():
        raise FileNotFoundError(f"dbt não encontrado no ambiente Python: {dbt_cli}. Instale requirements.txt no mesmo ambiente.")
    raw_con = duckdb.connect(str(db), read_only=True)
    try:
        configs = [json.loads(x[0]) for x in raw_con.execute("select date_formats_json::varchar from raw_files where sheet_role='transactions'").fetchall()]
    finally:
        raw_con.close()
    formats = sorted({fmt for c in configs for fmt in c.get("date_formats", {}).values()})
    dbt_vars = json.dumps({"date_formats": formats, "client_id": CONFIG["client_id"],
                           "corporate_card_routes": CONFIG.get("corporate_card_routes", {}),
                           "classification_review_rules": CONFIG.get("classification_review_rules", []),
                           "reimbursement_issue_date_rule": CONFIG.get("reimbursement_issue_date_rule"),
                           "first_automated_competence": args.first_competence,
                           "as_of_date": args.as_of_date.isoformat()})
    dbt_project = out / "dbt_project"
    shutil.copytree(ROOT / "dbt", dbt_project)
    shutil.copy2(args.resolutions.resolve(), dbt_project / "seeds" / "resolutions.csv")
    subprocess.run([str(dbt_cli), "build", "--project-dir", str(dbt_project), "--profiles-dir", str(dbt_project), "--target-path", str(out / "dbt_target"), "--log-path", str(out / "logs"), "--vars", dbt_vars], check=True, cwd=ROOT, env={**os.environ, "PIPELINE_DB": str(db), "DBT_PROFILES_DIR": str(dbt_project)})
    con = duckdb.connect(str(db), read_only=True)
    try:
        export_tables(con, out)
        write_controller_summary(con, out, args)
        summary_tables = ["raw_files", "raw_uber_occurrences", "raw_layouts", "raw_reference_inventory", "raw_issued_titles", "stg_uber_transactions", "stg_uber_statements", "int_transaction_versions", "int_transactions", "int_transactions_resolved", "int_transaction_conflicts", "int_transaction_integrity", "int_uber_email_links", "int_requester_email_links", "int_transaction_enrichment", "int_eats_orders", "compliance_transaction_flags", "dq_enrichment_issues", "dq_normalization_events", "dq_report", "int_monthly_cost_center_payment_summary", "int_uber_vendor_candidates", "dq_reference_issues", "int_ap_component_candidates", "int_ap_title_candidates", "int_ap_allocation_candidates", "int_ap_release_gate", "int_statement_detail_reconciliation", "ap_ajustes_candidatos", "ap_titulos_candidatos", "ap_titulos", "ap_rateios_candidatos", "ap_rateios_linhagem", "ap_rateios"]
        summary_tables += [f"raw_ref_{entity}" for entity in AUX_SPECS]
        (out / "run_summary.json").write_text(json.dumps({
            "counts": {t: con.execute(f"select count(*) from {t}").fetchone()[0] for t in summary_tables},
            "code_sha256": code_digest(),
            "input_manifest_sha256": digest(out / "input_manifest.json"),
            "issued_ledger_sha256": digest(args.issued_ledger),
            "resolutions_sha256": digest(args.resolutions),
            "python_version": sys.version.split()[0],
            "as_of_date": args.as_of_date.isoformat(),
            "first_automated_competence": args.first_competence,
        }, indent=2), encoding="utf-8", newline="\r\n")
    finally:
        con.close()


def publish_output(out, target_out):
    backup = target_out.with_name(f".{target_out.name}.previous-{uuid.uuid4().hex}")
    if target_out.exists():
        try:
            target_out.replace(backup)
        except PermissionError as exc:
            raise RuntimeError(f"Não foi possível substituir {target_out}: feche os arquivos abertos nessa pasta "
                               "(Excel, DuckDB) e execute de novo.") from exc
    try:
        out.replace(target_out)
    except Exception:
        if backup.exists():
            backup.replace(target_out)
        raise
    if backup.exists():
        if backup.parent != target_out.parent or not (backup / ".uber_pipeline_output").is_file():
            raise RuntimeError(f"Backup inesperado preservado para revisão: {backup}")
        shutil.rmtree(backup)


def export_tables(con, out):
    tables = ["raw_files", "raw_uber_occurrences", "raw_layouts", "raw_reference_inventory", "raw_issued_titles", *[f"raw_ref_{entity}" for entity in AUX_SPECS], "stg_uber_transactions", "stg_uber_statements", "int_transaction_versions", "int_transactions", "int_transactions_resolved", "int_transaction_conflicts", "int_transaction_integrity", "resolution_events", "dim_internal_email_lookup", "dim_internal_user_enrichment", "int_uber_email_links", "int_requester_email_links", "int_transaction_enrichment", "int_eats_orders", "compliance_transaction_flags", "dq_enrichment_issues", "dq_normalization_events", "dq_report", "int_monthly_cost_center_payment_summary", "int_uber_vendor_candidates", "dq_reference_issues", "int_ap_component_candidates", "int_ap_title_candidates", "int_ap_allocation_line_candidates", "int_ap_allocation_candidates", "int_ap_release_gate", "int_statement_detail_reconciliation", "ap_ajustes_candidatos", "ap_titulos_candidatos", "ap_titulos", "ap_rateios_candidatos", "ap_rateios_linhagem", "ap_rateios"]
    for table in tables:
        rows = con.execute(f"select * from {table}").description
        headers = [x[0] for x in rows]
        data = con.execute(f"select * from {table} order by all").fetchall()
        # ERP import files: plain UTF-8 (no BOM) per the Alchemy layout; audit CSVs keep BOM for Excel.
        encoding = "utf-8" if table in ERP_IMPORT_TABLES else "utf-8-sig"
        with (out / f"{table}.csv").open("w", encoding=encoding, newline="") as f:
            w = csv.writer(f); w.writerow(headers)
            for row in data:
                w.writerow([json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v for v in row])


def write_controller_summary(con, out, args):
    def rows(sql):
        return con.execute(sql).fetchall()
    fmt = lambda value: "—" if value is None else f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    titles = rows("select tipo, count(*) total, count(*) filter (where is_released) released from int_ap_release_gate group by tipo order by tipo")
    route = rows("select payment_route, sum(candidate_count), sum(known_amount_count), sum(missing_amount_count), sum(disputed_amount_count), sum(parse_failed_amount_count), sum(quarantined_candidate_count), sum(known_brl_subtotal) from int_monthly_cost_center_payment_summary group by payment_route order by payment_route")
    statements = rows("select competence, statement_total, known_component_subtotal, amount_unknown_count, quarantined_count from int_ap_title_candidates where tipo='FATURA_FORNECEDOR' and statement_total is not null order by competence")
    statement_conflicts = rows("select num_documento, statement_occurrence_count, statement_version_count from int_ap_title_candidates where tipo='FATURA_FORNECEDOR' and statement_version_count>1 order by num_documento")
    dq = rows("select dq_bucket, count(*) from dq_report group by dq_bucket order by dq_bucket")
    link_status = dict(rows("select email_link_status,count(*) from int_uber_email_links group by email_link_status"))
    vendor_name_duplicates = con.execute("select count(*) from dq_report where issue_code='uber_vendor_name_multiple_candidates'").fetchone()[0]
    blocker_counts = dict(rows("select blocker, count(*) from int_ap_release_gate, unnest(final_release_blockers) u(blocker) group by blocker"))
    top_centers = rows("select cost_center, sum(candidate_count), sum(known_brl_subtotal) from int_monthly_cost_center_payment_summary where payment_route='company_billed' and cost_center<>'UNATTRIBUTED' group by cost_center order by sum(known_brl_subtotal) desc nulls last, cost_center limit 3")
    unattributed = rows("select sum(candidate_count), sum(known_brl_subtotal) from int_monthly_cost_center_payment_summary where cost_center='UNATTRIBUTED' and payment_route='company_billed'")[0]
    billed_months = rows("select reporting_month, sum(candidate_count), sum(known_brl_subtotal), sum(missing_amount_count+disputed_amount_count+parse_failed_amount_count) from int_monthly_cost_center_payment_summary where payment_route='company_billed' group by reporting_month order by reporting_month")
    lines = ["# Resumo para o controller", "", "Os arquivos de importação incluem somente títulos aprovados pelo release gate. Subtotais de BRL conhecido são diagnósticos parciais quando há valor ausente, disputa, falha de parsing ou quarentena; não representam o total devido.", "", "## Contas a pagar"]
    for typ, total, released in titles:
        lines.append(f"- {typ}: {total} candidatos, {released} liberados, {total-released} retidos.")
    lines.append(f"- Arquivos Alchemy: {con.execute('select count(*) from ap_titulos').fetchone()[0]} títulos e {con.execute('select count(*) from ap_rateios').fetchone()[0]} rateios liberados.")
    lines.append(f"- Corte automatizado configurado: {args.first_competence}; data-base operacional: {args.as_of_date}. Títulos de competências anteriores, títulos já emitidos e vencimentos passados ficam retidos.")
    if con.execute("select count(*) from raw_issued_titles").fetchone()[0] == 0:
        lines.append("- Cadastro de títulos já emitidos vazio nesta execução. Confirmar o universo manual diretamente no ERP antes de qualquer importação futura.")
    lines.extend(["", "## Faturas por demonstrativo"])
    for month, statement, known, missing, quarantined in statements:
        lines.append(f"- {month}: demonstrativo {fmt(statement)}; subtotal BRL conhecido de detalhes {fmt(known)}; {missing} valores ausentes/disputados e {quarantined} candidatos em quarentena. Não se completou a diferença.")
    for month, charge_gap, fee_gap, unknown, integrity, due in rows("select competence, charge_residual, fee_residual, unknown_charge_count, integrity_issue_count, due_alert from int_statement_detail_reconciliation order by competence"):
        lines.append(f"- Conciliação do detalhe {month}: diferença de cobranças {fmt(charge_gap)}, diferença de taxas {fmt(fee_gap)}, {unknown} componentes de cobrança sem valor seguro, {integrity} problemas de integridade e vencimento `{due}`. A diferença não foi lançada por ajuste automático.")
    for number, occurrence_count, version_count in statement_conflicts:
        lines.append(f"- Demonstrativo {number or '(sem número)'}: {version_count} versões divergentes em {occurrence_count} ocorrências; valor devido indeterminado; fatura retida (`statement_versions_conflict`). Valores alternativos, não somados:")
        versions = con.execute("select s.source_file, s.source_sheet, s.source_row, s.source_line_start, s.source_line_end, s.file_sha256, r.total_raw, s.statement_total from stg_uber_statements s join raw_ref_statements r on r.file_sha256=s.file_sha256 and r.source_sheet is not distinct from s.source_sheet and r.source_row=s.source_row where s.statement_number is not distinct from ? order by s.source_file, s.source_sheet nulls first, s.source_row", [number]).fetchall()
        for source_file, source_sheet, source_row, line_start, line_end, sha, raw_total, parsed_total in versions:
            location = f"{source_file}, registro {source_row}"
            if source_sheet:
                location += f", aba {source_sheet}"
            if line_start is not None:
                location += f", linha física {line_start}" if line_start == line_end else f", linhas físicas {line_start}–{line_end}"
            lines.append(f"  - {location}, SHA-256 {sha[:16]}…: valor bruto `{raw_total}`; interpretado {fmt(parsed_total)}.")
    lines.extend(["", "## Visão mensal de rota"])
    for payment, count, known_count, missing, disputed, parse_failed, quarantined, subtotal in route:
        lines.append(f"- {payment}: {count} chaves candidatas; {known_count} valores conhecidos elegíveis ao subtotal, {missing} ausentes, {disputed} disputados, {parse_failed} com falha de parsing, {quarantined} em quarentena; subtotal conhecido {fmt(subtotal)}. É um subtotal do universo desta rota, não valor liberado de AP.")
    lines.extend(["", "## Insights reconciliados"])
    lines.append("- Maiores centros no faturamento de empresa, por subtotal de BRL conhecido (candidatos, não títulos liberados): " + ("; ".join(f"{cc}: {n} chaves, {fmt(amount)} conhecido" for cc, n, amount in top_centers) or "nenhum centro atribuído com valor conhecido") + f". No mesmo universo company_billed, UNATTRIBUTED contém {unattributed[0] or 0} chaves e subtotal conhecido {fmt(unattributed[1])}; sem rateio imputado.")
    if billed_months:
        lines.append("- Faturamento empresa por mês (subtotal conhecido, com lançamentos de valor desconhecido separados): " + "; ".join(f"{month}: {n} chaves, {fmt(amount)} conhecido, {unknown} ausente/disputado/falha" for month, n, amount, unknown in billed_months) + ". Como há componentes sem valor e nenhuma fatura foi liberada, isso não permite concluir variação mensal do total devido.")
    lines.append("- Rotas fora do faturamento desta integração permanecem visíveis: AMEX corporativo é excluído para processo próprio; VISA 0042 está pendente de decisão. Os subtotais dessas rotas não são contas a pagar liberadas.")
    lines.extend(["", "## Qualidade e pendências"])
    lines.append("- DQ por bucket (registros de issue, podem haver vários por candidato): " + (", ".join(f"{bucket}={count}" for bucket, count in dq) or "sem ocorrências") + ". Consulte `dq_report.csv` para localizadores e lineage.")
    for code, count, amount in rows("select expense_code,count(*),sum(amount_brl) from int_ap_component_candidates where cost_expense_review_required group by 1 order by 1"):
        lines.append(f"- Custo × Despesa pendente: {code}, {count} componentes / {fmt(amount)}. A pendência bloqueia o título e o rateio até decisão da controladoria.")
    for status, count, amount in rows("select employment_at_ride_status,count(*),sum(amount_brl) from int_transaction_enrichment where employment_at_ride_status in ('after_termination','before_admission') group by 1 order by 1"):
        lines.append(f"- RH: {status}, {count} componentes / {fmt(amount)}. Corridas fora da vigência requerem revisão; status corrente inativo não bloqueia por si só corridas históricas faturadas à empresa.")
    for code, count in rows("select issue_code,count(*) from dq_enrichment_issues where issue_code like 'mobility_%' group by 1 order by 1"):
        lines.append(f"- Compliance: {code}, {count} alertas para RH/gestor. A política não reduz o valor devido à Uber.")
    lines.append("- Decisões para liberar AP:")
    if blocker_counts.get('issue_date_missing') or blocker_counts.get('issue_date_missing_or_invalid_in_source'):
        lines.append("  - Informar a regra/fonte autorizada para `data_emissao` das faturas; o demonstrativo fornece apenas `data_disponibilizacao`. Podemos usá-la como emissão? Até a resposta, não foi tratada como emissão.")
    if blocker_counts.get('needs_client_reimbursement_issue_date_rule'):
        lines.append("  - Definir a regra ou fornecer documento com data de emissão para reembolsos; a data de vencimento candidata não resolve a emissão.")
    premise_titles = con.execute("select count(*) from int_ap_release_gate where issue_date_basis like 'config:%'").fetchone()[0]
    if premise_titles:
        lines.append(f"  - Confirmar a premissa operacional adotada neste case: `data_emissao` do reembolso = último dia do mês de competência ({premise_titles} candidatos, `issue_date_basis=config:last_day_of_competence_month`). Não há documento de origem com essa data; em produção depende de validação do cliente.")
    if blocker_counts.get('admin_fee_allocation_rule_pending') or blocker_counts.get('stage3_gate:admin_fee_allocation_rule_pending'):
        lines.append("  - Definir como ratear `Admin Fee` por centro de custo/contas; hoje bloqueia integralmente a fatura.")
    if blocker_counts.get('managerial_suggestion_disagrees_with_official_crosswalk'):
        lines.append("  - Confirmar a divergência gerencial de EVENTO; nenhuma sugestão foi aplicada automaticamente.")
    if blocker_counts.get('official_crosswalk_missing') or blocker_counts.get('stage3_gate:official_crosswalk_missing'):
        lines.append("  - Decidir Custo × Despesa do transporte noturno e fornecer crosswalk oficial para TRANSP-FUNC; a sugestão não preenche essa lacuna.")
    if blocker_counts.get('accounting_account_not_postable') or blocker_counts.get('stage3_gate:account_not_postable'):
        lines.append("  - Definir/substituir a conta contábil sintética TREIN por conta postável e confirmar crosswalk.")
    if blocker_counts.get('needs_client_card_destination'):
        lines.append("  - Confirmar destino/processo contábil da VISA corporativa final 0042; não foi convertida em reembolso pessoal.")
    if blocker_counts.get('amount_not_known') or blocker_counts.get('periodic_billing_detail_has_unknown_amount'):
        lines.append("  - Fornecer/evidenciar BRL para o lançamento CLP sem conversão ou preencher fontes que sustentem os componentes ausentes/disputados; a diferença do demonstrativo não foi usada como plug.")
    if blocker_counts.get('canonical_candidate_retained') or blocker_counts.get('periodic_billing_detail_has_quarantined_candidate'):
        lines.append("  - Revisar os 2 grupos de chave com valores conflitantes e registrar decisão explícita de ocorrência, sem somar versões.")
    if con.execute("select count(*) from int_monthly_cost_center_payment_summary where payment_route='needs_client_card_destination'").fetchone()[0]:
        lines.append("  - Classificar o débito em conta da VISA corporativa final 0042; a conciliação bancária separada encontra o movimento de R$ 33,20.")
    if link_status.get('ambiguous') or link_status.get('not_found'):
        lines.append(f"- Confirmar as ligações de email Uber pendentes: {link_status.get('ambiguous',0)} ambiguidades e {link_status.get('not_found',0)} não encontrados; não escolher usuário por nome/Employee ID.")
    if vendor_name_duplicates:
        lines.append("- Cadastro: há duplicidade nominal de fornecedores Uber. As faturas atuais foram ligadas pelo CNPJ do demonstrativo a um registro único; confirmar/limpar o cadastro para evitar ambiguidade futura.")
    from bank_reconciliation import discover_bank_files, bank_entries, candidates, reconcile
    bank_files=discover_bank_files(args.input)
    lines.extend(['', '## Evidência bancária'])
    if len(bank_files)==1:
        bank_titles, bank_cards=candidates(out / 'canonical.duckdb')
        bank_titles, card_matches, _=reconcile(bank_titles, bank_cards, bank_entries(bank_files[0]))
        lines.append(f"Fonte: {bank_files[0].name}. Pagamento no extrato não comprova baixa no ERP. Bloqueios de importação não excluem a pesquisa bancária.")
        for t in bank_titles:
            if t['duplicate_cents']:
                lines.append(f"- {t['name']} / {t['competence']}: título {fmt(Decimal(t['cents'])/100)}, pagamento principal {fmt(Decimal(t['paid_cents'])/100)} e duplicidade {fmt(Decimal(t['duplicate_cents'])/100)}; verificar restituição/compensação.")
            elif t['paid_cents'] is None:
                lines.append(f"- {t['name']} / {t['competence']}: {t['status']}, título {fmt(Decimal(t['cents'])/100) if t['cents'] is not None else 'indeterminado'}; conferir ERP/comprovante antes de ação financeira.")
            elif t['kind']=='FATURA_FORNECEDOR' or t['difference_cents']:
                lines.append(f"- {t['name']} / {t['competence']}: documento {fmt(Decimal(t['cents'])/100)}, débito principal {fmt(Decimal(t['paid_cents'])/100)}, diferença {fmt(Decimal(t['difference_cents'])/100)}; composição/classificação de diferenças depende de evidência.")
        reimbursements=[t for t in bank_titles if t['kind']=='REEMBOLSO_COLABORADOR']
        lines.append(f"- Reembolsos: {sum(t['paid_cents'] is not None for t in reimbursements)} títulos com pagamento associado; principal {fmt(sum(Decimal(t['paid_cents'] or 0) for t in reimbursements)/100)}, duplicidades {fmt(sum(Decimal(t['duplicate_cents']) for t in reimbursements)/100)}.")
        lines.append(f"- Débitos de cartão associados: {len(card_matches)}, {fmt(sum(Decimal(m['value']) for m in card_matches))}; classificação contábil ainda pendente.")
    else:
        lines.append('Não há um único extrato identificado na entrada; executar a conciliação separadamente com a fonte selecionada.')
    lines.extend(["", "Os números por rota e centro de custo estão em `int_monthly_cost_center_payment_summary.csv`. Os arquivos detalhados da conciliação são gerados por `bank_reconciliation.py` em `reconciliation/`, com movimentos únicos e valores atribuídos por título. Nenhuma baixa no ERP é executada.", ""])
    (out / "controller_summary.md").write_text("\n".join(lines), encoding="utf-8", newline="\r\n")
    (out / 'README.md').write_text('''# Entregáveis gerados

Os CSVs, os manifestos JSON e os documentos desta pasta são versionados. O banco DuckDB, cópias dbt, logs e testes permanecem locais.

| Entregável | Arquivo |
|---|---|
| Transações normalizadas | stg_uber_transactions.csv |
| Candidatos canônicos, resolvidos e conflitos | int_transactions.csv, int_transactions_resolved.csv, int_transaction_conflicts.csv |
| Vínculo por e-mail | int_uber_email_links.csv |
| Resumo mensal por CC e rota | int_monthly_cost_center_payment_summary.csv |
| Imports Alchemy | ap_titulos.csv, ap_rateios.csv |
| Retenções e linhagem | ap_titulos_candidatos.csv, ap_rateios_candidatos.csv, ap_rateios_linhagem.csv |
| Qualidade e normalizações | dq_report.csv, dq_normalization_events.csv |
| Resumo financeiro | controller_summary.md |
| Proveniência | input_manifest.json, run_summary.json |

Os imports podem conter apenas cabeçalhos: consultar os bloqueios dos candidatos. Valores conhecidos não substituem valores ausentes ou disputados.
Conciliação bancária: ../reconciliation/README.md. Análise e arquitetura: ../docs/18_analise_final_pipeline.md. Execução: ../RUNNING.md.
''',encoding='utf-8',newline='\r\n')


if __name__ == "__main__":
    main()
