select 'raw_to_staging' as invariant
where (select count(*) from {{ source('raw', 'raw_uber_occurrences') }}) <> (select count(*) from {{ ref('stg_uber_transactions') }})
union all
select 'staging_to_versions'
where (select count(*) from {{ ref('stg_uber_transactions') }}) <> (select count(*) from {{ ref('int_transaction_versions') }})
union all
select 'views_partition_candidates'
where (select count(*) from {{ ref('int_transactions') }}) <> (select count(*) from {{ ref('int_transactions_resolved') }}) + (select count(*) from {{ ref('int_transaction_conflicts') }})
union all
select 'view_overlap'
where exists (select transaction_id from {{ ref('int_transactions_resolved') }} intersect select transaction_id from {{ ref('int_transaction_conflicts') }})
union all
select 'missing_or_double_occurrence_coverage'
where exists (
  select occurrence_id from {{ source('raw', 'raw_uber_occurrences') }}
  except select occurrence_id from {{ ref('int_transaction_versions') }}
) or exists (
  select occurrence_id from {{ ref('int_transaction_versions') }} group by occurrence_id having count(*) <> 1
) or exists (
  select occurrence_id from {{ ref('int_transaction_versions') }}
  except select occurrence_id from {{ source('raw', 'raw_uber_occurrences') }}
)
