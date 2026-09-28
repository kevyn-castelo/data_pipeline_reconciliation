{{ config(materialized='table') }}

with joined as (
  select t.id_externo, t.tipo, t.candidate_group_key,
         c.transaction_id, c.business_key, c.occurrence_ids, c.trip_id,
         c.payment_route_status, c.company_billing_competence_utc, c.reimbursement_competence_local,
         c.linked_employee_number, c.responsibility_email, c.amount_brl, c.amount_status,
         c.official_cost_center as centro_custo,
         c.accounting_target_account as conta_contabil,
         c.official_managerial_account as conta_gerencial,
         c.allocation_dimensions_valid, c.amount_known, c.is_quarantined,
         c.component_blockers,
         -- A line is ready only when its component has no blocker of any kind, not just valid dimensions.
         case when c.allocation_dimensions_valid and c.amount_known and not c.is_quarantined
                   and coalesce(array_length(c.component_blockers),0)=0 then 'ready'
              else 'blocked_component' end as allocation_status,
         case when coalesce(array_length(c.component_blockers),0)=0 and c.allocation_dimensions_valid and c.amount_known and not c.is_quarantined
              then 'none' else coalesce(nullif(array_to_string(c.component_blockers, '|'),''), 'dimensions_or_amount_invalid') end as allocation_blocker_key
  from {{ ref('int_ap_title_candidates') }} t
  join {{ ref('int_ap_component_candidates') }} c using(candidate_group_key)
  where t.tipo in ('FATURA_FORNECEDOR','REEMBOLSO_COLABORADOR')
), numbered as (
  select *,
         coalesce(centro_custo,'<NULL>') || '|' || coalesce(conta_contabil,'<NULL>') || '|' ||
         coalesce(conta_gerencial,'<NULL>') || '|' || allocation_status || '|' || allocation_blocker_key as line_group_key
  from joined
)
select * from numbered
