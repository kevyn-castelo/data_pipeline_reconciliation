{{ config(materialized='view') }}
select * from {{ ref('int_transactions') }} where not is_quarantined
