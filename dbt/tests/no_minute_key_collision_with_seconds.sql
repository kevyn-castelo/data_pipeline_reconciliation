with collisions as (
  select trip_id, date_trunc('minute', transaction_ts_utc) as minute_utc, transaction_type
  from {{ ref('stg_uber_transactions') }}
  group by trip_id, date_trunc('minute', transaction_ts_utc), transaction_type
  having count(*) > 1 and bool_or(second(transaction_ts_utc) <> 0 or date_part('microsecond', transaction_ts_utc) <> second(transaction_ts_utc) * 1000000)
)
select * from collisions
