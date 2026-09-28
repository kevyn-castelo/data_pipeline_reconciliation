{{ config(materialized='view') }}
select * from {{ ref('int_transactions') }} where is_quarantined
