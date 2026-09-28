"""Evidências reproduzíveis do parecer de revisão independente (somente leitura).

Executar na raiz: & '.\\.venv\\Scripts\\python.exe' docs\\parecer_consultas.py
Não altera o banco nem os dados de origem; o extrato é apenas listado, sem pareamento automático.
"""

from pathlib import Path
import csv
import duckdb

ROOT = Path(__file__).resolve().parents[1]
con = duckdb.connect(str(ROOT / "output" / "canonical.duckdb"), read_only=True)

QUERIES = {
    "A_residuo_demonstrativo_vs_detalhe": """
        select company_billing_competence_utc competencia, transaction_type='Admin Fee' admin_fee,
               count(*) n, sum(amount_brl) filter(where amount_status='known' and not is_quarantined) conhecido
        from int_transaction_enrichment where payment_route_status='company_billed' group by all order by all
    """,
    "A_versoes_em_conflito_e_valor_ausente": """
        select v.occurrence_id, v.key_status, s.source_file, s.trip_id, s.amount_brl, s.tips_brl,
               s.amount_local, s.local_currency
        from int_transaction_versions v join stg_uber_transactions s using(occurrence_id)
        where v.business_key in (select business_key from int_transactions where is_quarantined or amount_status<>'known')
        order by s.trip_id, s.source_file
    """,
    "B_valor_brl_diferente_do_local_em_brl": """
        select occurrence_ids, trip_id, amount_local, amount_brl, amount_brl-amount_local diferenca
        from int_transactions where local_currency='BRL' and amount_local<>amount_brl
    """,
    "B_datas_impossiveis": """
        select occurrence_ids, trip_id, transaction_type, request_ts_local, dropoff_ts_local, transaction_ts_utc
        from int_transactions
        where dropoff_ts_utc < request_ts_utc or request_ts_local > timestamp '2026-09-01 23:59:59'
    """,
    "C_papel_do_complemento": """
        select t.key_status, e.payment_route_status, strftime(t.transaction_ts_utc,'%Y-%m') mes,
               count(*) n, sum(t.amount_brl) valor
        from int_transactions t join int_transaction_enrichment e using(transaction_id)
        where list_contains(list_transform(t.occurrence_ids, x -> split_part(x, ':', 1)), '305a20222a085961')
        group by all order by all
    """,
    "D_codigo_despesa_por_cc_natureza": """
        select e.expense_code, e.accounting_target_account, e.official_cost_center, c.description,
               count(*) n, sum(e.amount_brl) valor
        from int_transaction_enrichment e
        left join raw_ref_cost_centers c on c.cost_center=e.official_cost_center
        where e.expense_code in ('ENTRE-UN','TRANSP-FUNC') group by all order by all
    """,
    "E_corridas_apos_desligamento": """
        select e.linked_employee_number, emp.employee_name, emp.termination_date, e.request_ts_local,
               e.amount_brl, e.stage3_financial_gate
        from int_transaction_enrichment e join raw_ref_employees emp on emp.employee_number=e.linked_employee_number
        where emp.termination_date is not null order by e.request_ts_local
    """,
    "F_emails_nao_ligados_e_evidencia": """
        select e.email, e.email_link_status, e.uber_employee_id_raw, count(*) n, sum(e.amount_brl) valor
        from int_transaction_enrichment e where e.email_link_status in ('not_found','ambiguous')
        group by all order by all
    """,
    "F_diretorio_candidatos": """
        select user_id, primary_email, alternate_emails, employee_number, status
        from raw_ref_internal_users
        where employee_number in ('1013','1020','1041','1054','1021','1026') or user_id='U9003'
        order by employee_number, user_id
    """,
    "F_employee_id_diverge_da_matricula": """
        select email, linked_employee_number, uber_employee_id_raw, count(*) n
        from int_transaction_enrichment
        where email_link_status='linked' and coalesce(uber_employee_id_raw,'--')<>'--'
          and ltrim(uber_employee_id_raw,'0')<>ltrim(coalesce(linked_employee_number,''),'0')
        group by all
    """,
    "G_eats_por_pedido_acima_do_teto": """
        select trip_id, count(*) transacoes, sum(amount_brl) total_pedido
        from int_transaction_enrichment where lower(service) like '%eats%'
        group by trip_id having sum(amount_brl) > 80 order by total_pedido desc
    """,
    "G_eats_pedidos_vs_transacoes": """
        select count(*) transacoes, count(distinct trip_id) pedidos
        from int_transaction_enrichment where lower(service) like '%eats%'
    """,
    "G_fim_de_semana_sinalizado": """
        select c.transaction_id, e.transaction_type, c.assessed_local_ride_ts, c.amount_brl
        from compliance_transaction_flags c join int_transaction_enrichment e using(transaction_id)
        where c.weekend_policy_status='policy_violation_weekend_program' order by 3
    """,
    "H_dq_mesmo_codigo_em_buckets_diferentes": """
        select issue_code, list(distinct dq_bucket) buckets, count(*) n
        from dq_report group by 1 having count(distinct dq_bucket)>1
    """,
    "H_normalizacoes_nao_registradas": """
        select source_file,
               count(*) filter (where json_extract_string(canonical_values,'$.email')
                                <> lower(trim(json_extract_string(canonical_values,'$.email')))) email_normalizado,
               count(*) filter (where json_extract_string(canonical_values,'$.expense_code')
                                <> upper(trim(json_extract_string(canonical_values,'$.expense_code')))) codigo_normalizado
        from stg_uber_transactions group by 1 order by 1
    """,
    "H_technical_changes_por_campo": """
        select split_part(c,':',1) campo, source_file, count(*) n
        from stg_uber_transactions, unnest(technical_changes) u(c) group by all order by all
    """,
    "I_titulos_reembolso": """
        select competence, beneficiario_nome, valor_total_candidato, data_vencimento, is_released
        from int_ap_release_gate where tipo='REEMBOLSO_COLABORADOR' order by competence, beneficiario_nome
    """,
    "I_faturas": """
        select competence, num_documento, statement_total, data_vencimento, is_released
        from int_ap_release_gate where tipo='FATURA_FORNECEDOR' order by competence
    """,
}

for title, sql in QUERIES.items():
    print(f"\n### {title}")
    result = con.execute(sql)
    print(" | ".join(d[0] for d in result.description))
    for row in result.fetchall():
        print(" | ".join(str(v) for v in row))

# Extrato: somente listagem dos débitos Uber/PIX, para conferência manual no parecer.
lines = (ROOT / "data" / "extrato_itau_cc_2026-07_a_2026-09.csv").read_text(encoding="cp1252").splitlines()
header = next(i for i, line in enumerate(lines) if line.lower().startswith("data;lan"))
print("\n### J_extrato_debitos_uber_e_pix")
for row in csv.reader(lines[header + 1:], delimiter=";"):
    if row[3].strip() and ("UBER" in row[1].upper() or row[1].startswith("PIX TRANSF")):
        print(" | ".join(row[:4]))
