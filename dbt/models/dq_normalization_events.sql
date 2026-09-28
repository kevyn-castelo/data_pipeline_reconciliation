{{ config(materialized='table') }}

with base as (
  select v.transaction_id, v.business_key, s.*
  from {{ ref('stg_uber_transactions') }} s
  join {{ ref('int_transaction_versions') }} v using(occurrence_id)
), events as (
  select *, 'normalized_email' as issue_code,
         json_extract_string(canonical_values,'$.email') as before_value,
         coalesce(email,'<NULL>') as after_value
  from base
  where json_extract_string(canonical_values,'$.email') is not null
    and json_extract_string(canonical_values,'$.email') is distinct from email
  union all by name
  select *, 'normalized_expense_code' as issue_code,
         json_extract_string(canonical_values,'$.expense_code') as before_value,
         coalesce(expense_code,'<NULL>') as after_value
  from base
  where json_extract_string(canonical_values,'$.expense_code') is not null
    and json_extract_string(canonical_values,'$.expense_code') is distinct from expense_code
  union all by name
  select *, 'normalized_amount_brl_format' as issue_code,
         json_extract_string(canonical_values,'$.amount_brl') as before_value,
         cast(amount_brl as varchar) as after_value
  from base
  where json_extract_string(canonical_values,'$.amount_brl') like '%,%'
    and amount_brl is not null
  union all by name
  select *, 'normalized_request_local_datetime' as issue_code,
         concat_ws(' ',json_extract_string(canonical_values,'$.request_date_local'),
                       json_extract_string(canonical_values,'$.request_time_local')) as before_value,
         cast(request_ts_local as varchar) as after_value
  from base
  where json_extract_string(canonical_values,'$.request_date_local') like '%/%'
    and request_ts_local is not null
  union all by name
  select *, 'normalized_dropoff_local_datetime' as issue_code,
         concat_ws(' ',json_extract_string(canonical_values,'$.dropoff_date_local'),
                       json_extract_string(canonical_values,'$.dropoff_time_local')) as before_value,
         cast(dropoff_ts_local as varchar) as after_value
  from base
  where json_extract_string(canonical_values,'$.dropoff_date_local') like '%/%'
    and dropoff_ts_local is not null
), text_events as (
  select b.transaction_id, b.business_key, b.occurrence_id, b.source_file, b.source_sheet,
         b.source_row, b.source_line_start, b.source_line_end, b.amount_brl,
         'normalized_' || change.field_name as issue_code,
         coalesce(nullif(change.original,''), '<EMPTY>') as before_value,
         coalesce(change.normalized, '<NULL>') as after_value
  from base b cross join unnest([
    struct_pack(field_name := 'trip_id', original := json_extract_string(canonical_values,'$.trip_id'), normalized := trip_id),
    struct_pack(field_name := 'transaction_type', original := json_extract_string(canonical_values,'$.transaction_type'), normalized := transaction_type),
    struct_pack(field_name := 'uber_employee_id_raw', original := json_extract_string(canonical_values,'$.uber_employee_id_raw'), normalized := uber_employee_id_raw),
    struct_pack(field_name := 'first_name', original := json_extract_string(canonical_values,'$.first_name'), normalized := first_name),
    struct_pack(field_name := 'last_name', original := json_extract_string(canonical_values,'$.last_name'), normalized := last_name),
    struct_pack(field_name := 'uber_group', original := json_extract_string(canonical_values,'$.uber_group'), normalized := uber_group),
    struct_pack(field_name := 'service', original := json_extract_string(canonical_values,'$.service'), normalized := service),
    struct_pack(field_name := 'program', original := json_extract_string(canonical_values,'$.program'), normalized := program),
    struct_pack(field_name := 'city', original := json_extract_string(canonical_values,'$.city'), normalized := city),
    struct_pack(field_name := 'country', original := json_extract_string(canonical_values,'$.country'), normalized := country),
    struct_pack(field_name := 'expense_memo', original := json_extract_string(canonical_values,'$.expense_memo'), normalized := expense_memo),
    struct_pack(field_name := 'payment_method_raw', original := json_extract_string(canonical_values,'$.payment_method_raw'), normalized := payment_method_raw),
    struct_pack(field_name := 'local_currency', original := json_extract_string(canonical_values,'$.local_currency'), normalized := local_currency),
    struct_pack(field_name := 'uber_invoice_number', original := json_extract_string(canonical_values,'$.uber_invoice_number'), normalized := uber_invoice_number)
  ]) u(change)
  where change.original is not null and change.original is distinct from change.normalized
), technical as (
  select b.transaction_id, b.business_key, b.occurrence_id, b.source_file, b.source_sheet,
         b.source_row, b.source_line_start, b.source_line_end, b.amount_brl,
         'normalized_' || split_part(change,':',1) as issue_code,
         regexp_extract(change,'^[^:]+:(.*)->',1) as before_value,
         regexp_extract(change,'->(.*)$',1) as after_value
  from base b cross join unnest(b.technical_changes) u(change)
), dedup as (
  select t.transaction_id, t.business_key, list_sort(t.occurrence_ids)[1] as occurrence_id,
         s.source_file, s.source_sheet, s.source_row, s.source_line_start, s.source_line_end,
         t.amount_brl, 'equivalent_occurrences_collapsed' as issue_code,
         array_to_string(list_sort(t.occurrence_ids),'|') as before_value,
         t.transaction_id as after_value
  from {{ ref('int_transactions') }} t
  join {{ ref('stg_uber_transactions') }} s on s.occurrence_id=list_sort(t.occurrence_ids)[1]
  where t.key_status='equivalent' and t.n_occurrences>1
)
select transaction_id, business_key, occurrence_id, source_file, source_sheet, source_row,
       source_line_start, source_line_end, amount_brl, issue_code, before_value, after_value
from events
union all select * from text_events
union all select * from technical
union all select * from dedup
