{{ config(materialized='table') }}

with users as (
  select user_id, count(*) as user_record_count,
         count(distinct coalesce(employee_number, '<NULL>')) as employee_number_count,
         min(employee_number) as employee_number,
         min(directory_cost_center) as directory_cost_center,
         min(status) as user_status,
         min(display_name) as display_name
  from {{ source('raw', 'raw_ref_internal_users') }}
  where nullif(trim(user_id), '') is not null
  group by user_id
), employees as (
  select employee_number, count(*) as employee_row_count,
         count(distinct coalesce(official_cost_center, '<NULL>')) as official_cc_value_count,
         count(distinct coalesce(cpf_digits, '<NULL>')) as cpf_value_count,
         min(employee_name) as employee_name,
         min(official_cost_center) as official_cost_center,
         min(status) as employee_status,
         min(admission_date) as admission_date_raw,
         min(termination_date) as termination_date_raw,
         bool_and(cpf_valid) as cpf_valid
  from {{ source('raw', 'raw_ref_employees') }}
  where nullif(trim(employee_number), '') is not null
  group by employee_number
), cost_centers as (
  select cost_center, count(*) as cc_row_count, min(description) as cost_center_name,
         min(active_flag) as active_flag
  from {{ source('raw', 'raw_ref_cost_centers') }}
  where nullif(trim(cost_center), '') is not null
  group by cost_center
)
select u.user_id, u.display_name, u.user_record_count, u.user_status,
       case when u.user_record_count > 1 then 'ambiguous_user_record'
            when upper(trim(u.user_status)) = 'ATIVO' then 'active'
            else 'inactive_or_suspended' end as user_status_check,
       case when u.employee_number_count = 1 then u.employee_number end as employee_number,
       case when u.employee_number_count > 1 then 'ambiguous_user_matricula'
            when u.employee_number is null or trim(u.employee_number) = '' then 'missing_employee_number'
            when e.employee_number is null then 'employee_not_found'
            when e.employee_row_count > 1 then 'ambiguous_employee'
            when upper(trim(e.employee_status)) <> 'ATIVO' then 'employee_inactive'
            else 'linked' end as employee_link_status,
       e.employee_name, e.employee_status, e.admission_date_raw, e.termination_date_raw,
       case when e.employee_row_count = 1 and e.cpf_value_count = 1 then e.cpf_valid end as employee_cpf_valid,
       case when e.employee_number is null then null when e.employee_row_count > 1 then 'ambiguous'
            when e.cpf_value_count > 1 then 'ambiguous'
            when e.cpf_value_count = 0 then 'missing' when e.cpf_valid then 'valid' else 'invalid' end as employee_cpf_status,
       case when e.official_cc_value_count = 1 then e.official_cost_center end as official_cost_center,
       u.directory_cost_center,
       case when e.employee_number is null then 'employee_not_found'
            when e.employee_row_count > 1 then 'ambiguous_employee'
            when e.official_cc_value_count > 1 then 'ambiguous_official_cost_center'
            when e.official_cost_center is null or trim(e.official_cost_center) = '' then 'missing_official_cost_center'
            when cc.cost_center is null then 'cost_center_not_found'
            when cc.cc_row_count > 1 then 'ambiguous_cost_center'
            when upper(trim(cc.active_flag)) not in ('S','SIM','ATIVO','TRUE','1') then 'cost_center_inactive'
            else 'active' end as official_cost_center_status,
       cc.cost_center_name,
       (nullif(upper(trim(u.directory_cost_center)), '') is not null and
        nullif(upper(trim(u.directory_cost_center)), '') <> nullif(upper(trim(e.official_cost_center)), '')) as directory_cost_center_mismatch
from users u
left join employees e on u.employee_number_count=1 and e.employee_number=u.employee_number
left join cost_centers cc on e.official_cost_center=cc.cost_center
