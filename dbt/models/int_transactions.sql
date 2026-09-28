{{ config(materialized='table') }}
{% set fields = [
  'trip_id','transaction_ts_utc','request_ts_utc','request_ts_local','dropoff_ts_utc','dropoff_ts_local','request_utc_offset_min',
  'email','requester_email','uber_employee_id_raw','first_name','last_name','uber_group','service','program','city','country',
  'expense_code','expense_memo','payment_method_raw','card_brand','card_last4','transaction_type','amount_brl','total_fare_brl',
  'employee_paid_brl','tips_brl','amount_local','local_currency','uber_invoice_number'
] %}
with joined as (
  select v.*, s.* exclude (occurrence_id, file_sha256, source_file, source_sheet, source_row, source_line_start, source_line_end, layout_id),
    coalesce(v.business_key, 'UNRESOLVED:' || v.occurrence_id) as candidate_id
  from {{ ref('int_transaction_versions') }} v join {{ ref('stg_uber_transactions') }} s using(occurrence_id)
), stats as (
  select candidate_id, business_key, transaction_id, min(key_status) as key_status,
    list_sort(list(occurrence_id)) as occurrence_ids,
    max(n_occurrences_key) as n_occurrences,
    list_sort(list_distinct(flatten(list(conflict_fields)))) as conflict_fields,
    bool_or(same_file_repeat) as same_file_repeat,
    bool_or(fare_duplicate_trip) as fare_duplicate_trip,
    bool_or(same_trip_type_multi_ts) as same_trip_type_multi_ts,
    list_sort(list_distinct(flatten(list(parse_errors)))) as group_parse_errors,
    list_sort(list_distinct(flatten(list(technical_changes)))) as group_technical_changes,
    {% for field in fields %}
    case when list_contains(list_sort(list_distinct(flatten(list(conflict_fields)))), '{{ field }}') then null else min({{ field }}) end as {{ field }}{% if not loop.last %},{% endif %}
    {% endfor %}
  from joined group by candidate_id, business_key, transaction_id
), decisions as (
  select s.*, e.resolution_status, e.resolution_action, e.chosen_occurrence_id,
         e.resolution_event,
         case when e.resolution_status = 'applied' and e.resolution_action = 'accept_occurrence' then true else false end as accepted
  from stats s left join {{ ref('resolution_events') }} e using(business_key)
), chosen as (
  select d.*, c.occurrence_id as selected_occurrence_exists, c.parse_errors as chosen_parse_errors,
         c.technical_changes as chosen_technical_changes,
         {% for field in fields %}
         c.{{ field }} as c_{{ field }}{% if not loop.last %},{% endif %}
         {% endfor %}
  from decisions d left join {{ ref('stg_uber_transactions') }} c on d.chosen_occurrence_id = c.occurrence_id
), effective as (
  select *,
    list_filter([
      case when business_key is null then 'identity_unresolved' end,
      case when transaction_type is not null and transaction_type not in ('Fare','Adjustment','Tip','Admin Fee') then 'unknown_transaction_type' end,
      case when fare_duplicate_trip then 'fare_duplicate_trip' end,
      case when same_file_repeat and not accepted then 'within_file_duplicate' end,
      case when len(conflict_fields) > 0 and not accepted then 'conflict' end,
      case when resolution_status = 'stale' then 'resolution_stale' end,
      case when resolution_status = 'applied' and resolution_action = 'reject_all' then 'rejected_by_decision' end
    ], x -> x is not null) as retention_reasons,
    case
      when accepted then case when list_contains(chosen_parse_errors, 'amount_brl:parse_error') then 'parse_failed' when c_amount_brl is null then 'missing_in_source' else 'known' end
      when list_contains(conflict_fields, 'amount_brl') then 'disputed'
      when list_contains(group_parse_errors, 'amount_brl:parse_error') then 'parse_failed'
      when amount_brl is not null then 'known'
      else 'missing_in_source'
    end as amount_status
  from chosen
)
select transaction_id, business_key, key_status, n_occurrences, occurrence_ids, conflict_fields, amount_status,
       coalesce(resolution_status, 'none') as resolution_status, resolution_action, chosen_occurrence_id,
       retention_reasons, len(retention_reasons) > 0 as is_quarantined,
       fare_duplicate_trip, same_trip_type_multi_ts,
       {% for field in fields %}
       case when accepted then c_{{ field }} else {{ field }} end as {{ field }}{% if not loop.last %},{% endif %}
       {% endfor %},
       case when accepted then chosen_parse_errors else group_parse_errors end as parse_errors,
       case when accepted then chosen_technical_changes else group_technical_changes end as technical_changes,
       resolution_event
from effective
