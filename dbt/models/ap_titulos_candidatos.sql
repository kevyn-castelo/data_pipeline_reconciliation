{{ config(materialized='view') }}
select * from {{ ref('int_ap_release_gate') }}
