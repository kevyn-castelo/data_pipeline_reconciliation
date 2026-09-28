with missing_or_changed as (
  select t.occurrence_ids
  from {{ ref('int_transactions') }} t
  left join {{ ref('int_transaction_enrichment') }} e using(occurrence_ids)
  where e.occurrence_ids is null
     or t.transaction_id is distinct from e.transaction_id
     or t.business_key is distinct from e.business_key
     or t.occurrence_ids is distinct from e.occurrence_ids
  union all
  select e.occurrence_ids
  from {{ ref('int_transaction_enrichment') }} e
  left join {{ ref('int_transactions') }} t using(occurrence_ids)
  where t.occurrence_ids is null
)
select * from missing_or_changed
