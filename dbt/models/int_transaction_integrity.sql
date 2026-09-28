{{ config(materialized='table') }}

with source_dates as (
  select t.occurrence_ids,
         min(try_cast(f.report_date_raw as timestamp)) as earliest_report_ts
  from {{ ref('int_transactions') }} t
  cross join unnest(t.occurrence_ids) u(occurrence_id)
  join {{ source('raw','raw_uber_occurrences') }} o on o.occurrence_id=u.occurrence_id
  join {{ source('raw','raw_files') }} f
    on f.file_sha256=o.file_sha256 and f.source_sheet is not distinct from o.source_sheet
   and f.sheet_role='transactions'
  group by t.occurrence_ids
)
select t.transaction_id, t.business_key, t.occurrence_ids, d.earliest_report_ts,
       list_filter([
         case when t.local_currency='BRL' and t.amount_brl is not null and t.amount_local is not null
                        and t.amount_brl <> t.amount_local then 'brl_local_amount_mismatch' end,
         case when t.request_ts_utc is not null and t.dropoff_ts_utc is not null
                        and t.dropoff_ts_utc < t.request_ts_utc then 'dropoff_before_request' end,
         case when t.request_ts_local is not null and d.earliest_report_ts is not null
                        and t.request_ts_local::date > d.earliest_report_ts::date then 'ride_after_report_date' end
       ], x -> x is not null) as integrity_issues
from {{ ref('int_transactions') }} t
left join source_dates d on d.occurrence_ids=t.occurrence_ids
