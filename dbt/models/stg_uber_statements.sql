{{ config(materialized='table') }}

with parsed as (
  select file_sha256, source_file, source_sheet, source_row, source_line_start, source_line_end,
         trim(statement_number) as statement_number,
         issuer_cnpj_raw,
         regexp_replace(coalesce(issuer_cnpj_raw,''), '[^0-9]', '', 'g') as issuer_cnpj_digits,
         try_strptime(trim(period_start_raw), '%d/%m/%Y')::date as period_start,
         try_strptime(trim(period_end_raw), '%d/%m/%Y')::date as period_end,
         try_strptime(trim(availability_date_raw), '%d/%m/%Y')::date as availability_date,
         try_strptime(nullif(trim(explicit_issue_date_raw),''), '%d/%m/%Y')::date as issue_date,
         try_strptime(trim(due_date_raw), '%d/%m/%Y')::date as due_date,
         trim(payment_method) as payment_method,
         case when regexp_matches(trim(user_charges_raw), '^[+-]?[0-9]+(\.[0-9]{3})*(,[0-9]{1,2})?$')
              then try_cast(replace(replace(trim(user_charges_raw), '.', ''), ',', '.') as decimal(15,2)) end as user_charges,
         case when regexp_matches(trim(service_fees_raw), '^[+-]?[0-9]+(\.[0-9]{3})*(,[0-9]{1,2})?$')
              then try_cast(replace(replace(trim(service_fees_raw), '.', ''), ',', '.') as decimal(15,2)) end as service_fees,
         case when regexp_matches(trim(total_raw), '^[+-]?[0-9]+(\.[0-9]{3})*(,[0-9]{1,2})?$')
              then try_cast(replace(replace(trim(total_raw), '.', ''), ',', '.') as decimal(15,2)) end as statement_total,
         regexp_matches(trim(user_charges_raw), '^[+-]?[0-9]+(\.[0-9]{3})*(,[0-9]{1,2})?$') as user_charges_text_valid,
         regexp_matches(trim(service_fees_raw), '^[+-]?[0-9]+(\.[0-9]{3})*(,[0-9]{1,2})?$') as service_fees_text_valid,
         regexp_matches(trim(total_raw), '^[+-]?[0-9]+(\.[0-9]{3})*(,[0-9]{1,2})?$') as total_text_valid,
         observation
  from {{ source('raw', 'raw_ref_statements') }}
)
select *,
       strftime(period_start, '%Y-%m') as competence,
       (period_start is not null and period_end is not null and strftime(period_start,'%Y-%m')=strftime(period_end,'%Y-%m')) as period_is_single_month,
       (period_start is not null and period_end is not null and period_start=date_trunc('month',period_start)::date and period_end=last_day(period_start)) as period_is_full_month,
       (user_charges is not null and service_fees is not null and statement_total is not null and user_charges + service_fees = statement_total) as statement_components_close,
       (statement_total > 0) as statement_total_positive
from parsed
