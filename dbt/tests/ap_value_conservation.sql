-- Money and row conservation from enrichment to allocation lines (not only counts).
with enr as (select count(*) as n, sum(amount_brl) as v from {{ ref('int_transaction_enrichment') }}),
outside as (
  select count(*) as n, coalesce(sum(amount_brl),0) as v from {{ ref('int_transaction_enrichment') }}
  where payment_route_status is null or payment_route_status not in ('company_billed','employee_reimbursement_candidate')
),
comp as (select count(*) as n, coalesce(sum(amount_brl),0) as v from {{ ref('int_ap_component_candidates') }}),
lines as (select count(*) as n, coalesce(sum(amount_brl),0) as v from {{ ref('int_ap_allocation_line_candidates') }}),
alloc as (select coalesce(sum(component_count),0) as n, coalesce(sum(known_amount_subtotal),0) as v from {{ ref('int_ap_allocation_candidates') }})
select 'enrichment_vs_components_plus_outside' as failure
where (select n from enr) <> (select n from comp) + (select n from outside)
   or coalesce((select v from enr),0) <> (select v from comp) + (select v from outside)
union all
select 'components_vs_allocation_lines'
where (select n from comp) <> (select n from lines) or (select v from comp) <> (select v from lines)
union all
select 'allocation_lines_vs_grouped_allocations'
where (select n from lines) <> (select n from alloc) or (select v from lines) <> (select v from alloc)
union all
select 'amount_status_inconsistent_with_amount'
where exists (select 1 from {{ ref('int_transactions') }} where (amount_status='known') <> (amount_brl is not null))
