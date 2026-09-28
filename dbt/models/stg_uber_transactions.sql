{{ config(materialized='table') }}

with b as (
  select o.*, f.file_format, f.workbook_epoch, f.date_formats_json,
         json_extract_string(f.date_formats_json, '$.decimal_separator') as decimal_separator
  from {{ source('raw', 'raw_uber_occurrences') }} o
  join {{ source('raw', 'raw_files') }} f on o.file_sha256 = f.file_sha256 and o.source_file = f.source_file and o.source_sheet is not distinct from f.source_sheet
  where f.sheet_role = 'transactions'
), p as (
  select b.*,
    nullif(lower(trim({{ rv('trip_id') }})), '') as trip_id,
    {{ parsed_ts(rv('transaction_ts_utc'), 'transaction_ts_utc', 'b.workbook_epoch') }} as transaction_ts_utc,
    case upper(trim({{ rv('transaction_type') }})) when 'FARE' then 'Fare' when 'TIP' then 'Tip' when 'ADJUSTMENT' then 'Adjustment' when 'ADMIN FEE' then 'Admin Fee' else nullif(trim({{ rv('transaction_type') }}), '') end as transaction_type,
    {{ parsed_money('amount_brl') }} as amount_brl,
    {{ parsed_money('total_fare_brl') }} as total_fare_brl,
    {{ parsed_money('employee_paid_brl') }} as employee_paid_brl,
    {{ parsed_money('tips_brl') }} as tips_brl,
    {{ parsed_money('amount_local') }} as amount_local,
    {{ parsed_ts(rv('request_date_utc'), 'request_date_utc', 'b.workbook_epoch') }} as request_date_utc_ts,
    {{ parsed_ts(rv('request_date_local'), 'request_date_local', 'b.workbook_epoch') }} as request_date_local_ts,
    {{ parsed_ts(rv('dropoff_date_utc'), 'dropoff_date_utc', 'b.workbook_epoch') }} as dropoff_date_utc_ts,
    {{ parsed_ts(rv('dropoff_date_local'), 'dropoff_date_local', 'b.workbook_epoch') }} as dropoff_date_local_ts
  from b
), t as (
  select p.*,
    {{ parsed_datetime('request_date_utc', 'request_time_utc', 'request_datetime_utc') }} as _request_utc,
    {{ parsed_datetime('request_date_local', 'request_time_local', 'request_datetime_local') }} as _request_local,
    {{ parsed_datetime('dropoff_date_utc', 'dropoff_time_utc', 'dropoff_datetime_utc') }} as _dropoff_utc,
    {{ parsed_datetime('dropoff_date_local', 'dropoff_time_local', 'dropoff_datetime_local') }} as _dropoff_local
  from p
), final as (
  select *,
    _request_utc as request_ts_utc, _request_local as request_ts_local,
    _dropoff_utc as dropoff_ts_utc, _dropoff_local as dropoff_ts_local,
    try_cast(regexp_extract(coalesce({{ rv('request_utc_offset') }}, ''), '^(-?)([0-9]{1,2}):([0-9]{2})', 2) as integer) * 60 *
      case when starts_with(coalesce({{ rv('request_utc_offset') }}, ''), '-') then -1 else 1 end
      + try_cast(regexp_extract(coalesce({{ rv('request_utc_offset') }}, ''), '^(-?)([0-9]{1,2}):([0-9]{2})', 3) as integer) *
      case when starts_with(coalesce({{ rv('request_utc_offset') }}, ''), '-') then -1 else 1 end as request_utc_offset_min,
    nullif(nullif(lower(trim({{ rv('email') }})), '--'), '') as email,
    nullif(trim({{ rv('uber_employee_id_raw') }}), '') as uber_employee_id_raw,
    nullif(trim({{ rv('first_name') }}), '') as first_name,
    nullif(trim({{ rv('last_name') }}), '') as last_name,
    nullif(trim({{ rv('uber_group') }}), '') as uber_group,
    nullif(trim({{ rv('service') }}), '') as service,
    nullif(trim({{ rv('program') }}), '') as program,
    nullif(upper(trim(nullif({{ rv('expense_code') }}, '--'))), '') as expense_code,
    nullif(trim(nullif({{ rv('expense_memo') }}, '--')), '') as expense_memo,
    nullif(trim({{ rv('payment_method_raw') }}), '') as payment_method_raw,
    nullif(upper(trim({{ rv('local_currency') }})), '') as local_currency,
    nullif(trim(nullif({{ rv('uber_invoice_number') }}, '--')), '') as uber_invoice_number,
    nullif(trim({{ rv('requester') }}), '') as requester_raw,
    nullif(trim({{ rv('country') }}), '') as country,
    nullif(trim({{ rv('city') }}), '') as city,
    nullif(regexp_extract(coalesce({{ rv('payment_method_raw') }}, ''), '(?i)^(.+?)\s+-\s+([0-9]{4})$', 1), '') as card_brand,
    nullif(regexp_extract(coalesce({{ rv('payment_method_raw') }}, ''), '(?i)^(.+?)\s+-\s+([0-9]{4})$', 2), '') as card_last4,
    nullif(lower(regexp_extract(coalesce({{ rv('requester') }}, ''), '(?i)solicitado por:\s*([^\s<>]+@[^\s<>]+)', 1)), '') as requester_email
  from t
)
select occurrence_id, file_sha256, source_file, source_sheet, source_row, source_line_start, source_line_end, layout_id,
       trip_id, transaction_ts_utc, request_ts_utc, request_ts_local, dropoff_ts_utc, dropoff_ts_local, request_utc_offset_min,
       email, requester_email, uber_employee_id_raw, first_name, last_name, uber_group, service, program, city, country,
       expense_code, expense_memo, payment_method_raw, card_brand, card_last4, transaction_type,
       amount_brl, total_fare_brl, employee_paid_brl, tips_brl, amount_local, local_currency, uber_invoice_number,
       original_values, canonical_values,
       list_filter([
         case when trip_id is null then 'trip_id:missing' end,
         case when transaction_ts_utc is null then 'transaction_ts_utc:parse_error_or_missing' end,
         case when transaction_type is null then 'transaction_type:missing' end,
         case when {{ rv('transaction_ts_utc') }} is not null and transaction_ts_utc is null then 'transaction_ts_utc:parse_error' end,
         case when (nullif({{ rv('request_date_utc') }}, '') is not null or nullif({{ rv('request_time_utc') }}, '') is not null) and request_ts_utc is null then 'request_ts_utc:parse_error' end,
         case when (nullif({{ rv('request_date_local') }}, '') is not null or nullif({{ rv('request_time_local') }}, '') is not null) and request_ts_local is null then 'request_ts_local:parse_error' end,
         case when (nullif({{ rv('dropoff_date_utc') }}, '') is not null or nullif({{ rv('dropoff_time_utc') }}, '') is not null) and dropoff_ts_utc is null then 'dropoff_ts_utc:parse_error' end,
         case when (nullif({{ rv('dropoff_date_local') }}, '') is not null or nullif({{ rv('dropoff_time_local') }}, '') is not null) and dropoff_ts_local is null then 'dropoff_ts_local:parse_error' end,
         case when nullif({{ rv('request_utc_offset') }}, '') is not null and request_utc_offset_min is null then 'request_utc_offset_min:parse_error' end,
         case when {{ rv('amount_brl') }} is not null and trim({{ rv('amount_brl') }}) not in ('', '--') and amount_brl is null then 'amount_brl:parse_error' end,
         case when {{ rv('total_fare_brl') }} is not null and trim({{ rv('total_fare_brl') }}) not in ('', '--') and total_fare_brl is null then 'total_fare_brl:parse_error' end,
         case when {{ rv('employee_paid_brl') }} is not null and trim({{ rv('employee_paid_brl') }}) not in ('', '--') and employee_paid_brl is null then 'employee_paid_brl:parse_error' end,
         case when {{ rv('tips_brl') }} is not null and trim({{ rv('tips_brl') }}) not in ('', '--') and tips_brl is null then 'tips_brl:parse_error' end,
         case when {{ rv('amount_local') }} is not null and trim({{ rv('amount_local') }}) not in ('', '--') and amount_local is null then 'amount_local:parse_error' end
       ], x -> x is not null) as parse_errors,
       list_filter([
         case when regexp_matches(coalesce({{ rv('transaction_ts_utc') }}, ''), '^[0-9]+([.][0-9]+)?$') and
                    abs(try_cast({{ rv('transaction_ts_utc') }} as decimal(38,15))*86400 - floor(try_cast({{ rv('transaction_ts_utc') }} as decimal(38,15))*86400+0.5)) > 0 and
                    abs(try_cast({{ rv('transaction_ts_utc') }} as decimal(38,15))*86400 - floor(try_cast({{ rv('transaction_ts_utc') }} as decimal(38,15))*86400+0.5)) < 0.000001
              then 'transaction_ts_utc:' || {{ rv('transaction_ts_utc') }} || '->' || cast(transaction_ts_utc as varchar) end,
         case when amount_brl is not null and try_cast(replace({{ rv('amount_brl') }}, ',', '.') as decimal(38,18)) <> amount_brl then 'amount_brl:' || {{ rv('amount_brl') }} || '->' || cast(amount_brl as varchar) end,
         case when total_fare_brl is not null and try_cast(replace({{ rv('total_fare_brl') }}, ',', '.') as decimal(38,18)) <> total_fare_brl then 'total_fare_brl:' || {{ rv('total_fare_brl') }} || '->' || cast(total_fare_brl as varchar) end,
         case when employee_paid_brl is not null and try_cast(replace({{ rv('employee_paid_brl') }}, ',', '.') as decimal(38,18)) <> employee_paid_brl then 'employee_paid_brl:' || {{ rv('employee_paid_brl') }} || '->' || cast(employee_paid_brl as varchar) end,
         case when tips_brl is not null and try_cast(replace({{ rv('tips_brl') }}, ',', '.') as decimal(38,18)) <> tips_brl then 'tips_brl:' || {{ rv('tips_brl') }} || '->' || cast(tips_brl as varchar) end,
         case when amount_local is not null and try_cast(replace({{ rv('amount_local') }}, ',', '.') as decimal(38,18)) <> amount_local then 'amount_local:' || {{ rv('amount_local') }} || '->' || cast(amount_local as varchar) end,
         case when nullif(nullif(trim({{ rv('expense_code') }}), '--'), '') is not null and upper(trim({{ rv('expense_code') }})) <> expense_code then 'expense_code:' || {{ rv('expense_code') }} || '->' || expense_code end
       ], x -> x is not null) as technical_changes
from final
