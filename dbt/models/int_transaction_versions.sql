{{ config(materialized='table') }}
{% set fields = [
  'transaction_ts_utc','request_ts_utc','request_ts_local','dropoff_ts_utc','dropoff_ts_local','request_utc_offset_min',
  'email','requester_email','uber_employee_id_raw','first_name','last_name','uber_group','service','program','city','country',
  'expense_code','expense_memo','payment_method_raw','transaction_type','amount_brl','total_fare_brl','employee_paid_brl',
  'tips_brl','amount_local','local_currency'
] %}
with keyed as (
  select s.*,
    case when trip_id is not null and transaction_ts_utc is not null and transaction_type is not null
      then trip_id || '|' || strftime(transaction_ts_utc, '%Y-%m-%dT%H:%M') || '|' || transaction_type end as business_key
  from {{ ref('stg_uber_transactions') }} s
), candidates as (
  select *, coalesce(business_key, 'UNRESOLVED:' || occurrence_id) as candidate_id
  from keyed
), conflict_stats as (
  select candidate_id,
    list_filter([
      {% for field in fields %}
      case when count(distinct case
        when {{ raw_available(field) }} then
          case when list_contains(parse_errors, '{{ field }}:parse_error') then 'E:' || coalesce(json_extract_string(canonical_values, '$.{{ field }}'), '')
               when {{ field }} is null then 'N:' else 'V:' || cast({{ field }} as varchar) end
        else null end) > 1 then '{{ field }}' end{% if not loop.last %},{% endif %}
      {% endfor %},
      case when count(distinct case when uber_invoice_number is not null then 'V:' || uber_invoice_number end) > 1 then 'uber_invoice_number' end
    ], x -> x is not null) as conflict_fields
  from candidates group by candidate_id
), repeats as (
  select candidate_id, bool_or(file_count > 1) as same_file_repeat
  from (select candidate_id, file_sha256, count(*) as file_count from candidates group by candidate_id, file_sha256)
  group by candidate_id
), trip_fares as (
  select trip_id, count(distinct business_key) filter (where transaction_type = 'Fare' and business_key is not null) as fare_keys
  from candidates where trip_id is not null group by trip_id
), trip_type_times as (
  select trip_id, transaction_type, count(distinct business_key) as timestamp_count
  from candidates where trip_id is not null and business_key is not null group by trip_id, transaction_type
), typed as (
  select c.*, cs.conflict_fields,
    count(*) over(partition by c.candidate_id) as n_occurrences_key,
    r.same_file_repeat,
    coalesce(tf.fare_keys > 1 and c.transaction_type = 'Fare', false) as fare_duplicate_trip,
    coalesce(tt.timestamp_count > 1, false) as same_trip_type_multi_ts,
    case
      when c.business_key is null then 'identity_unresolved'
      when r.same_file_repeat then 'within_file_duplicate'
      when len(cs.conflict_fields) > 0 then 'conflict'
      when count(*) over(partition by c.candidate_id) > 1 then 'equivalent'
      else 'single'
    end as key_status
  from candidates c join conflict_stats cs using(candidate_id)
  join repeats r using(candidate_id)
  left join trip_fares tf on c.trip_id = tf.trip_id
  left join trip_type_times tt on c.trip_id = tt.trip_id and c.transaction_type = tt.transaction_type
)
select occurrence_id, business_key,
  case when business_key is null then null else 'UBR|' || '{{ var("client_id") }}' || '|' || business_key end as transaction_id,
  sha256(to_json(struct_pack(trip_id, {% for field in fields %}{{ field }}, {% endfor %} uber_invoice_number, parse_errors))) as content_hash,
  n_occurrences_key, same_file_repeat, conflict_fields, key_status, fare_duplicate_trip, same_trip_type_multi_ts,
  file_sha256, source_file, source_sheet, source_row, source_line_start, source_line_end, layout_id
from typed
