{{ config(materialized='table') }}
select l.id_externo as id_externo_titulo, a.seq,
       l.transaction_id, l.business_key, l.trip_id, l.occurrence_ids,
       l.amount_brl, l.amount_status, l.component_blockers,
       l.payment_route_status, l.candidate_group_key,
       l.centro_custo, l.conta_contabil, l.conta_gerencial,
       l.allocation_status, l.allocation_blocker_key
from {{ ref('int_ap_allocation_line_candidates') }} l
join {{ ref('int_ap_allocation_candidates') }} a
  on a.id_externo=l.id_externo and a.line_group_key=l.line_group_key
