{{ config(materialized='view') }}
select l.id_externo as id_externo_titulo, l.seq, l.conta_contabil, l.conta_gerencial,
       l.centro_custo, l.line_amount as valor, t.competence as competencia,
       case when l.allocation_status='ready' then 'Rateio candidato Uber'
            else 'Rateio retido: ' || l.allocation_blocker_key end as historico,
       l.allocation_status, l.allocation_blocker_key, l.component_count,
       l.amount_unknown_count, l.occurrence_ids,
       t.is_released as title_is_released, t.final_release_blockers as title_release_blockers
from {{ ref('int_ap_allocation_candidates') }} l
join {{ ref('int_ap_release_gate') }} t using(id_externo)
