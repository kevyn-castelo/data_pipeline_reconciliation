with base as (
  select count(*) as n,
         sum(amount_brl) filter (where amount_status='known' and not is_quarantined) as known_brl
  from {{ ref('int_transaction_enrichment') }}
), summary as (
  select sum(candidate_count) as n, sum(known_brl_subtotal) as known_brl
  from {{ ref('int_monthly_cost_center_payment_summary') }}
)
select * from base cross join summary
where base.n <> summary.n or base.known_brl is distinct from summary.known_brl
