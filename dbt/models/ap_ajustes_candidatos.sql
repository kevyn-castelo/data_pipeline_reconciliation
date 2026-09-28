{{ config(materialized='table') }}

with lineage as (
  select candidate_group_key,
         list_sort(list_distinct(flatten(list(occurrence_ids)))) as occurrence_ids
  from {{ ref('int_ap_component_candidates') }} group by 1
)
select i.id_externo as id_externo_original, i.status as status_original,
       i.valor_total as valor_emitido, t.valor_total_candidato as valor_recalculado,
       (t.valor_total_candidato-i.valor_total)::decimal(15,2) as diferenca,
       'UBERAP-' || substr(sha256(i.id_externo || '|adjustment|' ||
         coalesce(array_to_string(l.occurrence_ids,'|'),'<NO_LINEAGE>') || '|' ||
         coalesce(cast(t.valor_total_candidato as varchar),'<UNKNOWN>')),1,32) as id_externo_ajuste_candidato,
       l.occurrence_ids,
       case when t.valor_total_candidato is null then 'source_value_unavailable'
            when t.valor_total_candidato=i.valor_total then 'no_change'
            when t.valor_total_candidato>i.valor_total then 'positive_adjustment_requires_approved_issue_and_due_dates'
            else 'negative_adjustment_requires_credit_process' end as adjustment_status
from {{ source('raw','raw_issued_titles') }} i
left join {{ ref('int_ap_title_candidates') }} t using(id_externo)
left join lineage l on l.candidate_group_key=t.candidate_group_key
