with expected(field_name) as (
  select unnest(['trip_id','transaction_ts_utc','transaction_type','amount_brl'])
)
select l.layout_id, e.field_name
from {{ source('raw', 'raw_layouts') }} l cross join expected e
where not list_contains(try_cast(l.field_availability_json as varchar[]), e.field_name)
