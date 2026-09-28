# Alchemy ERP — Accounts Payable import layout (v2)

Two UTF-8 CSV files, comma-separated, header row, `.` as decimal separator, dates `YYYY-MM-DD`.
Files are imported together; a payable whose allocation lines don't close is rejected as a whole.

## `ap_titulos.csv` — one row per payable

| Field | Type | Rules |
|---|---|---|
| `id_externo` | string(80) | **Idempotency key.** Unique per payable. Re-importing an existing `id_externo` updates it instead of creating a new payable. Must be stable across re-runs. |
| `tipo` | enum | `FATURA_FORNECEDOR` \| `REEMBOLSO_COLABORADOR` |
| `beneficiario_tipo` | enum | `PJ` \| `PF` |
| `beneficiario_documento` | string | CNPJ (14) or CPF (11), digits only, valid check digits. PJ must exist in the vendor master; PF must be an employee. |
| `beneficiario_nome` | string(120) | |
| `num_documento` | string(40) | Invoice number (for invoices). Optional for reimbursements. |
| `data_emissao` | date | |
| `data_vencimento` | date | |
| `competencia` | `YYYY-MM` | Accounting period of the expense. |
| `valor_total` | decimal(15,2) | > 0 |
| `moeda` | string(3) | `BRL` only. |
| `historico` | string(250) | Free text. |
| `origem` | string(40) | Source system / integration name. |

## `ap_rateios.csv` — allocation lines

| Field | Type | Rules |
|---|---|---|
| `id_externo_titulo` | string(80) | FK → `ap_titulos.id_externo` |
| `seq` | int | 1..n within the payable |
| `conta_contabil` | string | Must exist and accept postings (`aceita_lancamento = S`). |
| `conta_gerencial` | string | Must exist, accept postings, and be the crosswalk of `conta_contabil`. |
| `centro_custo` | string | Must exist and be active. |
| `valor` | decimal(15,2) | Sum of `valor` per payable **must equal** `valor_total` exactly. Negative lines allowed (credits/refunds) as long as the payable total is positive. |
| `competencia` | `YYYY-MM` | Optional; defaults to the payable's. |
| `historico` | string(250) | Optional. |

## Validation performed by the ERP on import
- Rejects the payable if any allocation line fails, if the lines don't add up, or if the beneficiary document is invalid.
- Does **not** detect duplicates other than by `id_externo`.
