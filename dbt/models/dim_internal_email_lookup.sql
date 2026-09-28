{{ config(materialized='table') }}

with addresses as (
  select nullif(lower(trim(primary_email)), '') as email_norm, user_id, 'primary' as link_method
  from {{ source('raw', 'raw_ref_internal_users') }} where nullif(trim(primary_email), '') is not null
  union all
  select nullif(lower(trim(alias)), '') as email_norm, user_id, 'alias' as link_method
  from {{ source('raw', 'raw_ref_internal_users') }}
  cross join unnest(string_split(coalesce(alternate_emails, ''), '|')) as a(alias)
  where nullif(trim(alias), '') is not null
)
select email_norm,
       count(distinct user_id) as candidate_user_count,
       list_sort(list_distinct(list(user_id))) as candidate_user_ids,
       string_agg(distinct link_method, '+' order by link_method) as matched_by
from addresses
where email_norm is not null and nullif(trim(user_id), '') is not null
group by email_norm
