{{ config(materialized='table') }}

with transaction_issues as (
  select d.transaction_id, d.business_key, d.occurrence_ids,
         r.source_file, r.source_sheet, r.source_row, r.source_line_start, r.source_line_end,
         d.issue_code, d.dq_bucket, d.issue_detail, d.amount_brl,
         e.amount_status, d.blocks_stage3,
         cast(null as varchar) as before_value, cast(null as varchar) as after_value,
         cast(null as varchar) as reference_entity
  from {{ ref('dq_enrichment_issues') }} d
  left join lateral (select unnest(list_sort(d.occurrence_ids)) as oid) u on true
  left join {{ source('raw','raw_uber_occurrences') }} r on r.occurrence_id=u.oid
  left join {{ ref('int_transaction_enrichment') }} e
    on e.occurrence_ids=d.occurrence_ids
  where d.issue_code <> 'directory_cost_center_mismatch'
), directory_corrections as (
  select e.transaction_id, e.business_key, e.occurrence_ids,
         r.source_file, r.source_sheet, r.source_row, r.source_line_start, r.source_line_end,
         'directory_cost_center_mismatch' as issue_code, 'auto_fixable' as dq_bucket,
         'Official HR cost center was used for attribution; directory value is preserved and was not overwritten.' as issue_detail,
         e.amount_brl, e.amount_status, false as blocks_stage3,
         u.directory_cost_center as before_value, u.official_cost_center as after_value,
         'directory_to_hr_cost_center' as reference_entity
  from {{ ref('int_transaction_enrichment') }} e
  left join {{ ref('dim_internal_user_enrichment') }} u on u.user_id=e.linked_user_id
  left join lateral (select unnest(list_sort(e.occurrence_ids)) as oid) x on true
  left join {{ source('raw','raw_uber_occurrences') }} r on r.occurrence_id=x.oid
  where e.directory_cost_center_mismatch
), normalization_issues as (
  select transaction_id, business_key, [occurrence_id] as occurrence_ids,
         source_file, source_sheet, source_row, source_line_start, source_line_end,
         issue_code, 'auto_fixable' as dq_bucket,
         'Deterministic source normalization or equivalent-occurrence consolidation.' as issue_detail,
         amount_brl, cast(null as varchar) as amount_status, false as blocks_stage3,
         before_value, after_value, 'source_normalization' as reference_entity
  from {{ ref('dq_normalization_events') }}
), reference_issues as (
  select cast(null as varchar) as transaction_id, cast(null as varchar) as business_key,
         cast([] as varchar[]) as occurrence_ids,
         source_file, source_sheet, source_row, cast(null as integer) as source_line_start,
         cast(null as integer) as source_line_end,
         issue_code, dq_bucket, issue_detail, cast(null as decimal(15,2)) as amount_brl,
         cast(null as varchar) as amount_status, blocks_stage3,
         cast(null as varchar) as before_value, cast(null as varchar) as after_value,
         entity_name as reference_entity
  from {{ ref('dq_reference_issues') }}
), payable_blockers as (
  select cast(null as varchar) as transaction_id, t.candidate_group_key as business_key,
         coalesce(c.occurrence_ids, []::varchar[]) as occurrence_ids,
         t.document_source_file as source_file, t.document_source_sheet as source_sheet,
         t.document_source_row as source_row, t.document_source_line_start as source_line_start,
         t.document_source_line_end as source_line_end,
         blocker as issue_code,
         case when blocker in ('issue_date_missing','issue_date_missing_or_invalid_in_source',
                               'needs_client_reimbursement_issue_date_rule','amount_not_known',
                               'periodic_billing_detail_has_unknown_amount','periodic_billing_detail_has_quarantined_candidate',
                               'official_crosswalk_missing','crosswalk_official_crosswalk_missing',
                               'managerial_suggestion_disagrees_with_official_crosswalk',
                               'admin_fee_allocation_rule_pending','expense_classification_suggestion_disagreement')
              then 'needs_client' else 'rule_based' end as dq_bucket,
         'AP candidate release blocker: ' || blocker as issue_detail,
         cast(null as decimal(15,2)) as amount_brl, cast(null as varchar) as amount_status,
         true as blocks_stage3, cast(null as varchar) as before_value, cast(null as varchar) as after_value,
         'payable_candidate' as reference_entity
  from {{ ref('int_ap_release_gate') }} g
  join {{ ref('int_ap_title_candidates') }} t on t.id_externo=g.id_externo
  cross join unnest(coalesce(g.final_release_blockers, []::varchar[])) u(blocker)
  left join (
    select candidate_group_key, list_sort(list_distinct(flatten(list(occurrence_ids)))) as occurrence_ids
    from {{ ref('int_ap_component_candidates') }} group by candidate_group_key
  ) c on c.candidate_group_key=t.candidate_group_key
)
, combined as (
  select * from transaction_issues
  union all select * from directory_corrections
  union all select * from normalization_issues
  union all select * from reference_issues
  union all select * from payable_blockers
)
select * exclude (dq_bucket),
       case when reference_entity='payable_candidate' then 'payable'
            when transaction_id is not null or array_length(occurrence_ids)>0 then 'occurrence'
            else 'reference' end as issue_grain,
       case when issue_code like 'email_link_%' or issue_code like 'employee_%' or issue_code like 'ride_%'
                      or issue_code like 'mobility_%' then 'RH'
            when issue_code like '%account%' or issue_code like '%crosswalk%' or issue_code like '%classification%'
                      or issue_code like '%cost_center%' then 'Controladoria'
            when reference_entity='payable_candidate' or issue_code like 'payment_route_%' then 'Financeiro'
            when issue_code like '%amount%' or issue_code like '%date%' then 'Uber/Financeiro'
            else 'Dados/Financeiro' end as issue_owner,
       case when blocks_stage3 then 'open_blocking' when dq_bucket='auto_fixable' then 'corrected'
            else 'open_informational' end as issue_status,
       case when issue_code like 'email_link_%' or issue_code in ('cost_expense_classification_pending', 'stage3_gate:cost_expense_classification_pending', 'former_employee_reimbursement_review', 'stage3_gate:former_employee_reimbursement_review', 'local_competence_missing','local_month_boundary_ambiguous')
            then 'needs_client' else dq_bucket end as dq_bucket
from combined
