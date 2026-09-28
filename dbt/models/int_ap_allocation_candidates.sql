{{ config(materialized='table') }}

with grouped as (
  select id_externo, tipo, candidate_group_key, line_group_key,
         centro_custo, conta_contabil, conta_gerencial, allocation_status, allocation_blocker_key,
         count(*) as component_count,
         count(*) filter(where not amount_known) as amount_unknown_count,
         sum(amount_brl) filter(where amount_known) as known_amount_subtotal,
         case when count(*) filter(where not amount_known)=0 then sum(amount_brl) end as line_amount,
         list_sort(list_distinct(flatten(list(occurrence_ids)))) as occurrence_ids
  from {{ ref('int_ap_allocation_line_candidates') }}
  group by id_externo, tipo, candidate_group_key, line_group_key, centro_custo, conta_contabil,
           conta_gerencial, allocation_status, allocation_blocker_key
), numbered as (
  select *, row_number() over(partition by id_externo order by centro_custo nulls last, conta_contabil nulls last,
                               conta_gerencial nulls last, allocation_status, allocation_blocker_key) as seq
  from grouped
)
select * from numbered
