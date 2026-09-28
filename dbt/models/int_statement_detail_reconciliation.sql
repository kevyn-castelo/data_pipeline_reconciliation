{{ config(materialized='table') }}

with details as (
  select company_billing_competence_utc as competence,
         count(*) filter(where transaction_type<>'Admin Fee') as charge_component_count,
         count(*) filter(where transaction_type='Admin Fee') as fee_component_count,
         count(*) filter(where transaction_type<>'Admin Fee' and not amount_known) as unknown_charge_count,
         count(*) filter(where transaction_type='Admin Fee' and not amount_known) as unknown_fee_count,
         sum(amount_brl) filter(where transaction_type<>'Admin Fee' and amount_known) as known_charges,
         sum(amount_brl) filter(where transaction_type='Admin Fee' and amount_known) as known_fees,
         count(*) filter(where array_length(integrity_issues)>0) as integrity_issue_count
  from {{ ref('int_ap_component_candidates') }}
  where payment_route_status='company_billed'
  group by 1
)
select t.id_externo, t.competence, t.num_documento, t.data_vencimento,
       t.user_charges, t.service_fees, t.statement_total,
       coalesce(d.known_charges,0)::decimal(15,2) as known_charges,
       coalesce(d.known_fees,0)::decimal(15,2) as known_fees,
       coalesce(d.charge_component_count,0) as charge_component_count,
       coalesce(d.fee_component_count,0) as fee_component_count,
       coalesce(d.unknown_charge_count,0) as unknown_charge_count,
       coalesce(d.unknown_fee_count,0) as unknown_fee_count,
       coalesce(d.integrity_issue_count,0) as integrity_issue_count,
       (t.user_charges-coalesce(d.known_charges,0))::decimal(15,2) as charge_residual,
       (t.service_fees-coalesce(d.known_fees,0))::decimal(15,2) as fee_residual,
       case when t.data_vencimento < cast('{{ var("as_of_date") }}' as date) then 'overdue'
            when t.data_vencimento <= cast('{{ var("as_of_date") }}' as date) + interval '7 days' then 'due_within_7_calendar_days'
            else 'not_due_soon' end as due_alert,
       case when t.statement_total is null then 'statement_value_unavailable'
            when d.unknown_charge_count>0 or d.unknown_fee_count>0 then 'residual_with_unknown_components'
            when t.user_charges is distinct from d.known_charges or t.service_fees is distinct from d.known_fees then 'unexplained_residual'
            else 'closed' end as reconciliation_status
from {{ ref('int_ap_release_gate') }} t
left join details d on d.competence=t.competence
where t.tipo='FATURA_FORNECEDOR'
