{{ config(materialized='table') }}

with employee_documents as (
  select employee_number, count(*) as employee_row_count,
         count(distinct coalesce(cpf_digits,'<NULL>')) as cpf_value_count,
         min(cpf_digits) as cpf_digits, min(cpf_valid) as cpf_valid,
         min(employee_name) as employee_name
  from {{ source('raw','raw_ref_employees') }}
  group by employee_number
)
select e.*, i.integrity_issues,
       case when e.payment_route_status='company_billed' then 'FATURA_FORNECEDOR'
            when e.payment_route_status='employee_reimbursement_candidate' then 'REEMBOLSO_COLABORADOR' end as payable_type,
       case when e.payment_route_status='company_billed' then 'statement-month:' || coalesce(e.company_billing_competence_utc,'UNASSIGNED')
            when e.payment_route_status='employee_reimbursement_candidate' then
              'reimbursement:' || coalesce('employee:' || e.linked_employee_number,
                                            'email:' || nullif(lower(trim(e.responsibility_email)),''),
                                            'unlinked') || ':' || coalesce(e.reimbursement_competence_local,'UNASSIGNED') end as candidate_group_key,
       coalesce(d.employee_row_count,0) as hr_employee_row_count,
       d.cpf_digits as beneficiary_cpf,
       d.cpf_valid as beneficiary_cpf_valid,
       d.employee_name as beneficiary_employee_name,
       (e.amount_status='known' and e.amount_brl is not null) as amount_known,
       (not e.cost_expense_review_required and e.official_cost_center_status='active'
        and e.accounting_account_validation_status='postable'
        and e.official_crosswalk_validation_status='mapped'
        and e.managerial_account_validation_status='postable'
        and e.accounting_target_account is not null and e.official_managerial_account is not null
        and e.official_cost_center is not null) as allocation_dimensions_valid,
       list_filter([
         case when e.cost_expense_review_required then 'cost_expense_classification_pending' end,
         case when array_length(i.integrity_issues)>0 then 'transaction_integrity_issue' end,
         case when e.is_quarantined then 'canonical_candidate_retained' end,
         case when e.stage3_financial_gate is distinct from 'candidate_for_stage3_review' then 'stage3_gate:' || coalesce(e.stage3_financial_gate,'missing') end,
         case when e.amount_status <> 'known' or e.amount_brl is null then 'amount_not_known' end,
         case when e.email_link_status is distinct from 'linked' then 'email_link_' || coalesce(e.email_link_status,'missing') end,
         case when e.employee_link_status is distinct from 'linked' then 'employee_link_' || coalesce(e.employee_link_status,'missing') end,
         case when e.official_cost_center_status is distinct from 'active' then 'official_cost_center_' || coalesce(e.official_cost_center_status,'missing') end,
         case when e.accounting_account_validation_status <> 'postable' then 'accounting_' || e.accounting_account_validation_status end,
         case when e.official_crosswalk_validation_status <> 'mapped' then 'crosswalk_' || e.official_crosswalk_validation_status end,
         case when e.managerial_account_validation_status <> 'postable' then 'managerial_' || e.managerial_account_validation_status end,
         case when e.managerial_suggestion_status='suggestion_disagrees_with_official_crosswalk' then 'managerial_suggestion_disagrees_with_official_crosswalk' end,
         case when e.transaction_type='Admin Fee' then 'admin_fee_allocation_rule_pending' end,
         case when e.payment_route_status='employee_reimbursement_candidate' and (e.employee_cpf_status is distinct from 'valid' or d.cpf_valid is not true or coalesce(d.employee_row_count,0) <> 1 or coalesce(d.cpf_value_count,0) <> 1) then 'beneficiary_cpf_invalid_or_missing_or_ambiguous' end,
         case when e.payment_route_status='employee_reimbursement_candidate' and e.local_month_boundary_ambiguous then 'local_month_boundary_ambiguous' end,
         case when e.payment_route_status='employee_reimbursement_candidate' and e.reimbursement_competence_local is null then 'local_competence_missing' end
       ], x -> x is not null) as component_blockers
from {{ ref('int_transaction_enrichment') }} e
left join {{ ref('int_transaction_integrity') }} i on i.occurrence_ids=e.occurrence_ids
left join employee_documents d on d.employee_number=e.linked_employee_number
where e.payment_route_status in ('company_billed','employee_reimbursement_candidate')
