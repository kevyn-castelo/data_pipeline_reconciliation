{{ config(materialized='table') }}

with candidates as (
  select v.*,
         regexp_replace(upper(coalesce(v.legal_name,'')), '[^A-Z0-9]', '', 'g') as normalized_vendor_name
  from {{ source('raw', 'raw_ref_vendors') }} v
  where regexp_matches(upper(coalesce(v.legal_name,'') || ' ' || coalesce(v.trade_name,'')), '(?i)UBER')
)
select *, count(*) over (partition by normalized_vendor_name) as same_name_candidate_count
from candidates
