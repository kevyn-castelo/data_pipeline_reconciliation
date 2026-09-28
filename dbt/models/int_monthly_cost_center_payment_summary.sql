{{ config(materialized='table') }}

with population as (
  select
    coalesce(company_billing_competence_utc,
             case when request_ts_local is not null then strftime(request_ts_local, '%Y-%m') end,
             reimbursement_competence_local,
             case when transaction_ts_utc is not null then strftime(transaction_ts_utc, '%Y-%m') end,
             'UNASSIGNED') as reporting_month,
    case when company_billing_competence_utc is not null then 'transaction_month_utc'
         when request_ts_local is not null then case when reimbursement_competence_local is not null then 'request_month_local' else 'request_month_local_non_ap_route' end
         when transaction_ts_utc is not null then 'transaction_month_utc_non_ap_route'
         else 'unassigned' end as reporting_month_basis,
    case when official_cost_center_status='active' then trim(official_cost_center) else 'UNATTRIBUTED' end as cost_center,
    case when official_cost_center_status='active' then 'attributed_to_active_hr_cost_center' else 'unattributed' end as attribution_status,
    coalesce(payment_route_status, 'payment_method_unknown') as payment_route,
    amount_status, amount_brl, is_quarantined
  from {{ ref('int_transaction_enrichment') }}
), grouped as (
  select reporting_month, reporting_month_basis, cost_center, attribution_status, payment_route,
         count(*) as candidate_count,
         count(*) filter (where amount_status='known' and not is_quarantined) as known_amount_count,
         count(*) filter (where amount_status='missing_in_source') as missing_amount_count,
         count(*) filter (where amount_status='disputed') as disputed_amount_count,
         count(*) filter (where amount_status='parse_failed') as parse_failed_amount_count,
         count(*) filter (where is_quarantined) as quarantined_candidate_count,
         count(*) filter (where amount_status <> 'known' or is_quarantined) as count_not_fully_valued_or_eligible,
         sum(amount_brl) filter (where amount_status='known' and not is_quarantined) as known_brl_subtotal
  from population
  group by all
)
select *,
       case when missing_amount_count + disputed_amount_count + parse_failed_amount_count + quarantined_candidate_count > 0
            then 'known_subtotal_not_total' else 'known_total_for_candidate_population' end as amount_label
from grouped
