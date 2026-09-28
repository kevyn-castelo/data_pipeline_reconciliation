{{ config(materialized='table') }}

with observed as (
  select distinct nullif(lower(trim(requester_email)), '') as email_norm
  from {{ ref('stg_uber_transactions') }} where nullif(trim(requester_email), '') is not null
)
select o.email_norm,
       case when l.email_norm is null then 'not_found' when l.candidate_user_count > 1 then 'ambiguous' else 'linked' end as email_link_status,
       case when l.candidate_user_count = 1 then l.candidate_user_ids[1] end as user_id,
       l.candidate_user_count, l.candidate_user_ids, l.matched_by,
       u.user_status, u.user_status_check, u.employee_number, u.employee_link_status,
       u.employee_name, u.employee_status, u.admission_date_raw, u.termination_date_raw,
       u.employee_cpf_status, u.employee_cpf_valid,
       u.directory_cost_center, u.official_cost_center, u.official_cost_center_status, u.cost_center_name,
       u.directory_cost_center_mismatch
from observed o
left join {{ ref('dim_internal_email_lookup') }} l using(email_norm)
left join {{ ref('dim_internal_user_enrichment') }} u on l.candidate_user_count=1 and u.user_id=l.candidate_user_ids[1]
