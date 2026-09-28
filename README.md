# Uber for Business → Alchemy ERP accounts payable

This repository implements the [Alchemy case requirements](TASK.md) for Indústria Madeireira Paraná Ltda. It reads the fictional Uber reports and client reference files in `data/`, produces canonical transactions and payable candidates, and records why a candidate cannot be imported. The optional bank reconciliation is a separate, read-only step. **Nothing connects to or posts into the ERP.**

## Reproduce locally

Use Git and Python **3.14.6** (the tested version). Dependency versions are pinned in [`requirements.txt`](requirements.txt). The first installation needs package-index access; the pipeline itself needs no API keys or external services. The full pipeline has been run on Windows. The macOS/Linux commands below use the same virtual-environment layout and have not yet been executed on those systems.

### Windows PowerShell

```powershell
git clone https://github.com/kevyn-castelo/data_pipeline_reconciliation.git
Set-Location .\data_pipeline_reconciliation
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py --input data --output output --as-of-date 2026-09-28
.\.venv\Scripts\python.exe bank_reconciliation.py --pipeline-output output --bank data\extrato_itau_cc_2026-07_a_2026-09.csv --output reconciliation
```

Run the checks after generating `output/canonical.duckdb`:

```powershell
.\.venv\Scripts\python.exe tests_data_controls.py
.\.venv\Scripts\python.exe tests_bank_reconciliation.py
.\.venv\Scripts\python.exe tests_synthetic.py
git diff --exit-code -- output reconciliation
```

### macOS or Linux shell

```bash
git clone https://github.com/kevyn-castelo/data_pipeline_reconciliation.git
cd data_pipeline_reconciliation
python3.14 --version
python3.14 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python run.py --input data --output output --as-of-date 2026-09-28
./.venv/bin/python bank_reconciliation.py --pipeline-output output --bank data/extrato_itau_cc_2026-07_a_2026-09.csv --output reconciliation
./.venv/bin/python tests_data_controls.py
./.venv/bin/python tests_bank_reconciliation.py
./.venv/bin/python tests_synthetic.py
git diff --exit-code -- output reconciliation
```

The pipeline build should end with **PASS=67, ERROR=0**; the three Python checks should pass. The final `git diff` should print nothing for this fixed input set, date and Python version. A separate Windows reproduction run matched all **52** versioned CSV/JSON/Markdown files in `output/` and all **8** in `reconciliation/` byte for byte. The tracked `output/` contains readable deliverables; its ignored DuckDB database, dbt artifacts and logs are recreated by `run.py`. Close any Excel or DuckDB handle on `output/` before rebuilding on Windows, because publication replaces that directory.

`--as-of-date` is explicit so overdue decisions and the reports are reproducible. For a new closing period, use the actual evaluation date. The configured first automated competence, **2026-09**, is a case assumption awaiting client confirmation before deployment; it prevents historical July/August reimport. `run.py` locates `dbt.exe` on Windows or `dbt` on macOS/Linux beside the virtual-environment Python. Report text uses fixed line endings to make generated files comparable across operating systems. macOS/Linux remain unverified by an end-to-end run.

## Deliverables in this repository

| `TASK.md` requirement | Open this result | How to read it |
|---|---|---|
| Normalized transactions and canonical decisions | [`output/stg_uber_transactions.csv`](output/stg_uber_transactions.csv), [`output/int_transactions.csv`](output/int_transactions.csv), [`output/int_transactions_resolved.csv`](output/int_transactions_resolved.csv) | RAW origin and conflicts remain traceable through `output/raw_uber_occurrences.csv` and `output/int_transaction_conflicts.csv`. |
| User linking and monthly cost-center view | [`output/int_uber_email_links.csv`](output/int_uber_email_links.csv), [`output/int_monthly_cost_center_payment_summary.csv`](output/int_monthly_cost_center_payment_summary.csv) | Includes link status, payment route and `UNATTRIBUTED`. |
| Alchemy payable and allocation imports | [`output/ap_titulos.csv`](output/ap_titulos.csv), [`output/ap_rateios.csv`](output/ap_rateios.csv) | Only fully approved titles and allocations reach these files. |
| Held payables and traceability | [`output/ap_titulos_candidatos.csv`](output/ap_titulos_candidatos.csv), [`output/ap_rateios_candidatos.csv`](output/ap_rateios_candidatos.csv), [`output/ap_rateios_linhagem.csv`](output/ap_rateios_linhagem.csv) | Review blocker codes and source occurrence IDs before any ERP action. |
| Three-bucket quality report | [`output/dq_report.csv`](output/dq_report.csv), [`output/dq_normalization_events.csv`](output/dq_normalization_events.csv) | `auto_fixable`, `rule_based` and `needs_client`; deterministic changes include before/after and source location. |
| Controller summary and business insights | [`output/controller_summary.md`](output/controller_summary.md), [`docs/18_analise_final_pipeline.md`](docs/18_analise_final_pipeline.md) | Architecture, financial bridge, cost-center analysis and client decisions. |
| Optional bank reconciliation | [`reconciliation/bank_reconciliation.csv`](reconciliation/bank_reconciliation.csv), [`reconciliation/README.md`](reconciliation/README.md) | Title, principal payment, duplicate, difference, bank movement and confidence are separate. |
| Design and operations | [`RUNNING.md`](RUNNING.md), [`output/README.md`](output/README.md) | Detailed runbook, output index, publication and remaining limits. |
| Design history and reviews | [`docs/README.md`](docs/README.md) | Numbered timeline from the first canonical-contract draft to the final analysis, with the current version of each document. |

For this sample, **588 Uber occurrences become 573 canonical candidates**. There are two invoice candidates and 18 reimbursement candidates. The ERP import CSVs contain **headers only**: no July/August title passes the configured competence, overdue and other release checks. The candidates and blocker columns show the amounts that were held; an empty import file does not mean that Uber spend or bank payments were zero. The bank report searches eligible candidate identities even when their ERP import is blocked, and never confirms an ERP settlement.

## How the pipeline works and how to operate it

`run.py` fingerprints each input and preserves source file, sheet/line and original values. DuckDB/dbt then builds staging, canonical candidates, e-mail → directory → employee → official cost-center links, accounting mappings, complete payable groups, release gates, quality issues and monthly summaries. `output/run_summary.json` records the input and code hashes, seed/ledger hashes, date and output counts. The build completes and passes dbt tests in a temporary sibling directory before `output/` is replaced. The bank step uses the built DuckDB database plus the chosen statement and writes separate reports; its rules are in [`config/reconciliation.json`](config/reconciliation.json).

For a later month, pass `--input <folder>` and the new `--as-of-date YYYY-MM-DD`; the loader identifies supported CSV/XLSX layouts by headers rather than file names. Supply `--bank <statement.csv>` to reconcile a different bank file. Review [`RUNNING.md`](RUNNING.md) before changing `--first-competence`, entering evidence-backed resolutions (`--resolutions`) or recording **actually issued** ERP titles (`--issued-ledger`). Stable external IDs and the issued-title ledger prevent duplicate imports across runs only when that ledger is maintained from ERP returns. Decisions about Custo × Despesa, unresolved identities, dates, invoice details and financial charges must be approved by the client; the pipeline does not invent them.

The original client profile, business rules and file inventory follow. They explain the joins and controls used by the implementation.

## Client context and source files

### Client profile

- Furniture manufacturer, head office in downtown Curitiba and factory in Araucária (PR), ~70
  employees using Uber for Business.
- Time zone: America/Sao_Paulo (UTC−3, no daylight saving). Occasional trips abroad.
- Runs a **dual chart of accounts**: the accounting chart (`plano_de_contas.csv`, *contábil*) and a
  managerial chart (`plano_gerencial.csv`, *gerencial*) used for the management P&L. The official
  crosswalk between them is `de_para_contabil_gerencial.csv`.
- Cost centers (`centros_de_custo.xlsx`) and departments (`departamentos.csv`) are separate
  hierarchies. **The cost center of record for an employee is the one in `funcionarios.xlsx`.**
- The Uber account of each person is identified by **e-mail**. E-mails live in the corporate
  directory export (`usuarios_internos.csv` — the same users that log into Alchemy ERP), which
  links each user to a matrícula. The company changed its e-mail domain a few years ago; older
  addresses are kept as aliases in the directory.
  The `Group` field in the Uber report is maintained by whoever administers the Uber account and
  is not reliable for accounting.

### Business rules (as described by the client's finance team)

1. **Company-billed usage** (`Payment Method` = `Periodic Billing`) is billed monthly by Uber. On the
   first business day of the following month Uber publishes the **Demonstrativo Mensal** (monthly
   statement: user charges + service fees), paid by boleto — see `demonstrativo_mensal_uber.csv`.
   Each statement becomes **one** payable to Uber, with the statement number, dates and total. A
   transaction belongs to the month of its **Transaction Timestamp (UTC)**, which is how Uber cuts
   the monthly report.
2. The allocation (*rateio*) of each statement is by the employee's **cost center** × the
   classification derived from the **Expense Code**: `de_para_codigo_despesa.csv` gives the
   conta contábil; the conta gerencial must be consistent with the official crosswalk.
3. For cards, Uber only shows **brand + last 4 digits** in `Payment Method` (e.g. `VISA - 1234`).
   The company's own cards are listed in `cartoes_corporativos.csv`. A ride paid with **any other
   card** was paid by the employee and is **reimbursed**: one payable per employee per month
   (month of the ride date in local time), due on the **15th of the following month**,
   beneficiary = the employee (CPF). Paid by PIX.
4. The corporate AMEX in `cartoes_corporativos.csv` is settled through the corporate-card
   statement, which has its own process — it is not part of the Uber statement nor of this
   integration.
5. The amount that matters for the company is the transaction amount **in BRL**. Amounts paid by
   the employee/guest (`Payments made by employees/guests`) are not charged to the company.
6. Mobility policy violations (see `politica_mobilidade.md`) must be reported to HR, but **do not
   change what the company owes Uber**.
7. Every Uber user must be **linked by e-mail to an internal user** (`usuarios_internos.csv`) and,
   through the matrícula, to the employee and their cost center. Finance wants to see the Uber
   spend **grouped by cost center** every month, including what could not be attributed.
8. Payables are imported into Alchemy ERP using `layout_importacao_contas_a_pagar.md`.

### Files in `data/`

| File | What it is |
|---|---|
| `uber_business_2026-07.csv` | July 2026 transactions — an **ad-hoc report** exported from the Uber for Business dashboard by the account admin on 31/07 at 20:00 (Brasília), before the month was over. |
| `uber_business_2026-08.xlsx` | August 2026 transactions — the **monthly report** downloaded from the Billing tab. The account uses a customized column set, and the file was received as XLSX. |
| `uber_business_2026-08_complemento_financeiro.csv` | Ad-hoc report around the turn of the month, exported by finance on 01/09 "to catch what was missing". Opened and saved in Excel before sending. |
| `demonstrativo_mensal_uber.csv` | Header data of the two Uber monthly statements (number, period, dates, user charges, service fees, total). |
| `cartoes_corporativos.csv` | The company's own payment cards (brand, last 4 digits, type). |
| `funcionarios.xlsx` | Employee master (HR): matrícula, CPF, department, cost center, status. |
| `usuarios_internos.csv` | Corporate directory / Alchemy ERP users export: user id, primary e-mail, alternative e-mails (aliases, `\|`-separated), matrícula, cost center as registered in the directory, status. |
| `centros_de_custo.xlsx` | Cost centers, with active flag. |
| `departamentos.csv` | Departments (and a reference cost center — not 1:1). |
| `plano_de_contas.csv` | Accounting chart. `aceita_lancamento` = S for analytic (postable) accounts. |
| `plano_gerencial.csv` | Managerial chart. |
| `de_para_contabil_gerencial.csv` | Official crosswalk contábil → gerencial. |
| `de_para_codigo_despesa.csv` | Uber Expense Code → conta contábil (and the gerencial the requester suggested). |
| `fornecedores.xlsx` | Vendor master. |
| `extrato_itau_cc_2026-07_a_2026-09.csv` | Itaú checking-account statement export, 01/07 to 20/09/2026 (for the optional reconciliation). |

Also in this folder: `politica_mobilidade.md` (client's mobility policy) and
`layout_importacao_contas_a_pagar.md` (Alchemy ERP import layout).

The reports follow Uber for Business's standard reporting layouts. Uber documents that columns can
be customized per account and that positions change over time. Documented transaction types are
`Fare`, `Adjustment` (including negative adjustments/refunds), `Tip` and `Admin Fee`; one trip may
have several transactions. See Uber's help center ("Reporting – CSV") and developer docs
("Download Transactional Data") if you want the official column dictionary.
