select business_key
from {{ ref('resolutions') }}
where business_key is null or trim(business_key) = ''
   or action is null or action not in ('accept_occurrence', 'reject_all')
   or decided_by is null or trim(decided_by) = ''
   or decided_at is null or trim(decided_at) = ''
   or reason is null or trim(reason) = ''
   or try_cast(occurrence_ids_seen as varchar[]) is null
   or len(try_cast(occurrence_ids_seen as varchar[])) = 0
   or try_cast(occurrence_ids_seen as varchar[]) is distinct from list_sort(list_distinct(try_cast(occurrence_ids_seen as varchar[])))
   or (action = 'accept_occurrence' and (chosen_occurrence_id is null or not list_contains(try_cast(occurrence_ids_seen as varchar[]), chosen_occurrence_id)))
   or (action = 'reject_all' and coalesce(chosen_occurrence_id, '') <> '')
union all
select business_key from {{ ref('resolutions') }} group by business_key having count(*) > 1
