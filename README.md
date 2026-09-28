# Indústria Madeireira Paraná Ltda — Uber for Business

## Client profile

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

## Business rules (as described by the client's finance team)

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

## Files in `data/`

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
