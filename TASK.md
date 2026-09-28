# Implementation Engineer Exercise — Uber for Business → Contas a Pagar

## Context

You're an Implementation Engineer at Alchemy ERP. Our client **Indústria Madeireira Paraná Ltda**,
a furniture manufacturer in Curitiba, is already live on Alchemy ERP. Their employees use
**Uber for Business** for rides (sales visits, airport, trips between the head office and the
factory, night-shift transport) and **Uber Eats** for overtime meals.

Today the finance team downloads the Uber reports every month, fixes them by hand in Excel and
types the payables into the ERP. They want us to automate it. They've sent two months of raw
exports plus the supporting files in `data/` (see `README.md` for the client's business rules and
a description of each file).

The Uber reports are not friendly: they come as CSV **or** XLSX, the two formats don't share the
same columns, there are title rows and footnotes mixed with the data, finance sometimes
re-exports an overlapping period, and a trip can appear more than once for legitimate reasons.
Every row must end up in the right payable, with the right cost center and the right
classification in both charts of accounts — or be explicitly held back with a reason.

## Your task

Design and build an **automated pipeline** that receives Uber for Business report files
(`.csv` or `.xlsx`) and produces:

1. **A normalized, canonical version of the Uber transactions** — one schema regardless of the
   source layout, consistent encodings, delimiters, date/time (and time zone), monetary formats
   and identifiers (CPF/CNPJ, e-mail, employee ID).

2. **User linking and cost-center view.** Link every Uber user to an internal user by **e-mail**
   (`usuarios_internos.csv`), and through the matrícula to the employee and cost center. Produce:
   - a linking table — one row per distinct Uber e-mail, with the internal user, matrícula, cost
     center, **how** it was linked, and the status (linked / ambiguous / not found);
   - a monthly summary **grouped by cost center** (count and BRL amount, split by payment type),
     with an explicit line for whatever could not be attributed.

3. **Contas a pagar ready for import into Alchemy ERP**, following
   `layout_importacao_contas_a_pagar.md`:
   - one payable per Uber invoice (*fatura*) for company-billed usage, with its cost allocation
     (*rateio*) by cost center × conta contábil × conta gerencial;
   - one reimbursement payable per employee per month for rides paid with a personal card.

4. **A data-quality report** that classifies every issue into one of three buckets:
   - **Auto-fixable** — corrected deterministically (and logged: what, where, before → after).
   - **Rule-based** — a validation rule rejected or quarantined it (balancing, impossible dates,
     duplicate/conflicting keys, employees or cost centers that don't exist or aren't active,
     Uber users that can't be linked (or link to more than one person), expense codes that don't map, postings to synthetic accounts, invoice vs. detail mismatch,
     CPF/CNPJ check digits…).
   - **Needs-client** — a genuine ambiguity you're escalating instead of guessing.

5. **A short written summary** for the client's controller: what was generated, what is
   blocked and why, what you fixed, and the specific questions that need an answer before the
   payables are released.

6. **Consolidation and insights.** This is an analyst role as much as an implementation one.
   Consolidate what was imported and tell the client's finance team what the data says —
   as a short analysis (notebook, dashboard, or a few charts + text; your choice). For example:
   where the Uber spend is (by cost center, type of use, month), how it's changing, how much of
   it is still pending a decision or couldn't be attributed and what that means for their
   numbers, and anything unusual you'd want them to look at. Every number you show must tie
   back to the payables and to what you held back.

### Differential (optional, but valued)

7. **Bank reconciliation.** Using `extrato_itau_cc_2026-07_a_2026-09.csv`, check which of the
   payables you generated were actually paid, and report: matched, matched with a difference
   (and what the difference is), still open, paid more than once, and bank debits that don't
   correspond to any payable. Explain your matching strategy and its confidence.

## What we're looking for

- **Correct joins.** Uber e-mail → internal users (`usuarios_internos.csv`) → matrícula →
  employees (`funcionarios.xlsx`) → cost centers (`centros_de_custo.xlsx`); expense code → `de_para_codigo_despesa.csv` → `plano_de_contas.csv`
  → `de_para_contabil_gerencial.csv` → `plano_gerencial.csv`; payment method → `cartoes_corporativos.csv`; payables → `demonstrativo_mensal_uber.csv`
  → vendor (`fornecedores.xlsx`); payables → bank statement. Choose your join keys deliberately and
  tell us why.
- **The payable has to close.** A payable is a legal/financial document: its amount must match
  the invoice, and its allocation lines must add up to it to the cent. When the detail doesn't
  support the invoice, we want to see how you handle it — not a silent plug.
- **Judgement about automation boundaries.** Some issues should be fixed silently, some should
  block a payable, and some must never be auto-decided. Anything that moves the client's income
  statement (e.g. Custo vs. Despesa, which moves CMV and Lucro Bruto) deserves special care.
- **Analysis, not just plumbing.** Once the data is in, can you turn it into something a
  controller would act on? We value a few well-chosen, correct insights over many charts —
  and we'll check that your totals reconcile with your payables and your quarantine.
- **Thoroughness.** The obvious problems are easy. The quieter ones — the ones that only show up
  when you relate files to each other or check totals — are what separate candidates.
- **Operability.** This will run every month, forever. Assume new files keep arriving, that
  finance will sometimes re-send or re-export an overlapping period, and that someone will ask
  six months from now *"where did this R$ 38,90 in this rateio line come from?"*. Re-running the
  pipeline on the same or overlapping inputs must not create duplicate payables, and every output
  should be traceable back to the original file and row.
- **Reproducibility.** We should be able to run your pipeline on a fresh copy of the files and
  get the same outputs and the same report.

## Constraints & notes

- Use whatever language/tools you like. Document how to run it.
- Don't hard-code for these specific files: next month the file name, the format (CSV vs XLSX)
  and the column order may change.
- Brazilian specifics matter: CPF/CNPJ check-digit validation, the Custo vs. Despesa distinction,
  the contábil/gerencial dual chart, and the fact that departments and cost centers are
  deliberately separate hierarchies (not 1:1).
- All data is fictional. Validate identifiers by algorithm, not by lookup. You don't need to call
  any real API — producing the import files is enough.
- Timebox: aim for a working pipeline and a clear report rather than exhaustive coverage of every
  edge case. Tell us what you'd do next given more time.

## Deliverables

- Your pipeline code, with instructions to run it.
- The normalized transaction output.
- The user-linking table and the cost-center summary.
- The Alchemy ERP import files (payables + allocation lines), plus whatever you held back.
- The data-quality report (three-bucket classification).
- The controller-facing summary.
- The consolidation and insights (notebook, dashboard, or document — with the numbers reconciling to the payables).
- *(Differential)* The bank reconciliation output and a short explanation of the approach.
- A short note on your design: how data moves through the pipeline, what you persist at each
  step, and how you'd operate it month after month.
