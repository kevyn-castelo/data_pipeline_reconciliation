"""Consultas reproduzíveis para a análise do pipeline, sem alterar o banco."""

from pathlib import Path
import csv
import json
from collections import Counter
import duckdb


DB = Path(__file__).resolve().parents[1] / "output" / "canonical.duckdb"
con = duckdb.connect(str(DB), read_only=True)

QUERIES = {
    "populacao": """
        select (select count(*) from raw_uber_occurrences) raw,
               (select count(*) from stg_uber_transactions) staging,
               (select count(*) from int_transactions) candidatos,
               (select count(*) from int_transactions_resolved) resolvidos,
               (select count(*) from int_transaction_conflicts) conflitos,
               (select count(*) from int_transaction_enrichment) enriquecidos
    """,
    "rotas": """
        select payment_route_status, count(*) n,
               count(*) filter(where amount_status='known' and not is_quarantined) n_valorado,
               count(*) filter(where amount_status<>'known' or is_quarantined) n_incompleto,
               sum(amount_brl) filter(where amount_status='known' and not is_quarantined) subtotal
        from int_transaction_enrichment group by 1 order by 1
    """,
    "ap": """
        select tipo, is_released, count(*) n, sum(valor_total_candidato) valor_titulos,
               sum(known_component_subtotal) subtotal_componentes
        from int_ap_release_gate group by 1,2 order by 1,2
    """,
    "ap_mes": """
        select tipo, competence, is_released, count(*) n,
               sum(valor_total_candidato) valor_titulos,
               sum(known_component_subtotal) subtotal_componentes
        from int_ap_release_gate group by 1,2,3 order by 1,2,3
    """,
    "faturas": """
        select competence, statement_total, user_charges, service_fees,
               known_component_subtotal, component_count, amount_unknown_count,
               allocation_dimension_error_count, allocation_line_count,
               blocked_allocation_line_count, ready_allocation_total
        from int_ap_release_gate where tipo='FATURA_FORNECEDOR' order by competence
    """,
    "reembolso_retido": """
        select competence, valor_total_candidato, component_count, final_release_blockers
        from int_ap_release_gate where tipo='REEMBOLSO_COLABORADOR' and not is_released
        order by competence
    """,
    "summary_mes_rota": """
        select reporting_month, payment_route, sum(candidate_count) n,
               sum(known_amount_count) n_valorado,
               sum(missing_amount_count) n_ausente,
               sum(disputed_amount_count) n_disputado,
               sum(quarantined_candidate_count) n_quarentena,
               sum(known_brl_subtotal) subtotal
        from int_monthly_cost_center_payment_summary group by 1,2 order by 1,2
    """,
    "cc_fatura": """
        select cost_center, sum(candidate_count) n,
               sum(known_brl_subtotal) subtotal
        from int_monthly_cost_center_payment_summary
        where payment_route='company_billed'
        group by 1 order by subtotal desc nulls last
    """,
    "tipo_uso": """
        select payment_route_status, coalesce(service,'<NULL>') service, count(*) n,
               sum(amount_brl) filter(where amount_status='known' and not is_quarantined) subtotal
        from int_transaction_enrichment group by 1,2 order by 1,4 desc nulls last
    """,
    "transacao_tipo": """
        select payment_route_status, transaction_type, count(*) n,
               sum(amount_brl) filter(where amount_status='known' and not is_quarantined) subtotal
        from int_transaction_enrichment group by 1,2 order by 1,2
    """,
    "links": """
        select email_link_status, matched_by, count(*) n
        from int_uber_email_links group by 1,2 order by 1,2
    """,
    "dq": "select dq_bucket, count(*) n from dq_report group by 1 order by 1",
    "dq_top": """
        select dq_bucket, issue_code, count(*) n
        from dq_report group by 1,2 order by n desc limit 25
    """,
    "controle": """
        select (select count(*) from ap_titulos) titulos,
               (select sum(valor_total) from ap_titulos) valor_titulos,
               (select count(*) from ap_rateios) rateios,
               (select sum(valor) from ap_rateios) valor_rateios,
               (select count(*) from ap_rateios_linhagem) componentes_rastreaveis,
               (select sum(known_brl_subtotal) from int_monthly_cost_center_payment_summary) universo_valorado
    """,
    "compliance": """
        select * from (describe compliance_transaction_flags)
    """,
    "cc_nao_atribuido": """
        select official_cost_center_status, email_link_status, employee_link_status,
               count(*) n, sum(amount_brl) filter(where amount_status='known' and not is_quarantined) subtotal
        from int_transaction_enrichment
        where payment_route_status='company_billed' and official_cost_center_status is distinct from 'active'
        group by 1,2,3 order by n desc
    """,
    "classificacao": """
        select expense_classification_status, count(*) n,
               sum(amount_brl) filter(where amount_status='known' and not is_quarantined) subtotal
        from int_transaction_enrichment
        where payment_route_status='company_billed'
        group by 1 order by n desc
    """,
    "compliance_status": """
        select 'weekend' regra, weekend_policy_status status, count(*) n from compliance_transaction_flags group by 1,2
        union all select 'black', black_service_policy_status, count(*) from compliance_transaction_flags group by 1,2
        union all select 'eats', eats_program_policy_status, count(*) from compliance_transaction_flags group by 1,2
        union all select 'eats_cap', eats_order_cap_assessment, count(*) from compliance_transaction_flags group by 1,2
        order by regra,status
    """,
    "bank_schema": """
        select count(*) as archive_present from raw_reference_inventory where entity_name='bank_statement' and source_present
    """,
    "tecnico": """
        select count(*) filter(where array_length(technical_changes)>0) n_ocorrencias_com_correcao,
               sum(array_length(technical_changes)) n_correcao_tecnica
        from stg_uber_transactions
    """,
    "status_canonico": """
        select key_status, count(*) n from int_transactions group by 1 order by 1
    """,
    "integridade_transacional": """
        select issue, count(*) n from int_transaction_integrity,
             unnest(integrity_issues) u(issue) group by 1 order by 1
    """,
    "vigencia_rh": """
        select employment_at_ride_status, count(*) n,
               sum(amount_brl) filter(where payment_route_status='company_billed') subtotal_faturado
        from int_transaction_enrichment group by 1 order by 1
    """,
}

for title, query in QUERIES.items():
    print(f"\n### {title}")
    result = con.execute(query)
    print(" | ".join(d[0] for d in result.description))
    for row in result.fetchall():
        print(" | ".join(str(value) for value in row))

bank = DB.parents[1] / "data" / "extrato_itau_cc_2026-07_a_2026-09.csv"
with bank.open(encoding="cp1252", newline="") as stream:
    lines = stream.readlines()
header_index = next(i for i, line in enumerate(lines) if line.lower().startswith("data;lançamento;"))
rows = list(csv.DictReader(lines[header_index:], delimiter=";"))
print("\n### preparo_banco")
print("headers | linhas | lancamentos_com_valor | linhas_de_saldo | descricoes_uber")
print(" | ".join(map(str, [list(rows[0]), len(rows),
                           sum(bool(row["valor (R$)"].strip()) for row in rows),
                           sum(bool(row["saldo (R$)"].strip()) for row in rows),
                           sorted({row["lançamento"] for row in rows if "UBER" in row["lançamento"].upper()})])))

run_results = json.loads((DB.parent / "dbt_target" / "run_results.json").read_text(encoding="utf-8"))
print("\n### ultimo_dbt_build")
print(run_results["metadata"]["generated_at"], dict(Counter(item["status"] for item in run_results["results"])))
