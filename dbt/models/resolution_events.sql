{{ config(materialized='table') }}
with current_sets as (
  select business_key, list_sort(list(occurrence_id)) as current_occurrence_ids,
         bool_or(key_status in ('conflict', 'within_file_duplicate')) as can_resolve
  from {{ ref('int_transaction_versions') }} where business_key is not null group by business_key
), rows as (
  select r.*,
    try_cast(r.occurrence_ids_seen as varchar[]) as seen_ids,
    c.current_occurrence_ids,
    case when c.business_key is null or not c.can_resolve then 'stale'
         when try_cast(r.occurrence_ids_seen as varchar[]) is distinct from c.current_occurrence_ids then 'stale'
         when r.action = 'accept_occurrence' and not list_contains(c.current_occurrence_ids, r.chosen_occurrence_id) then 'stale'
         else 'applied' end as resolution_status
  from {{ ref('resolutions') }} r left join current_sets c using(business_key)
)
select business_key, occurrence_ids_seen, seen_ids, current_occurrence_ids,
       action as resolution_action, chosen_occurrence_id, decided_by, decided_at, reason,
       resolution_status,
       case when resolution_status = 'stale' then 'RESOLUTION_STALE' end as resolution_event
from rows
