select transaction_id
from {{ ref('int_transaction_enrichment') }}
where stage3_financial_gate='candidate_for_stage3_review'
  and (
    is_quarantined
    or amount_status <> 'known'
    or email_link_status is distinct from 'linked'
    or linked_user_status is distinct from 'active'
    or employee_link_status is distinct from 'linked'
    or official_cost_center_status is distinct from 'active'
    or expense_classification_status <> 'mapped_to_postable_accounts'
    or transaction_type='Admin Fee'
    or payment_route_status not in ('company_billed','employee_reimbursement_candidate')
    or (payment_route_status='employee_reimbursement_candidate' and (employee_cpf_status<>'valid' or reimbursement_competence_local is null or local_month_boundary_ambiguous))
  )
