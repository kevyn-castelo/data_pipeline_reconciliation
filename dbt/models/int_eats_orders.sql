{{ config(materialized='table') }}

select trip_id,
       count(*) as transaction_count,
       count(*) filter(where transaction_type='Fare') as fare_count,
       count(*) filter(where amount_status<>'known' or is_quarantined) as unresolved_amount_count,
       sum(amount_brl) filter(where amount_status='known' and not is_quarantined) as known_order_total
from {{ ref('int_transaction_enrichment') }}
where lower(coalesce(service,'')) like '%eats%' and trip_id is not null
group by trip_id
