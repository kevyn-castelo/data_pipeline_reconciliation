{{ config(materialized='table') }}

{% set issue_fields = "transaction_id, business_key, occurrence_ids, amount_brl, issue_code, dq_bucket, issue_detail, blocks_stage3" %}

select transaction_id, business_key, occurrence_ids, amount_brl,
       'canonical_candidate_retained' as issue_code, 'rule_based' as dq_bucket,
       array_to_string(retention_reasons, ', ') as issue_detail, true as blocks_stage3
from {{ ref('int_transactions') }} where is_quarantined

union all
select i.transaction_id, i.business_key, i.occurrence_ids, t.amount_brl,
       issue as issue_code, 'rule_based' as dq_bucket,
       'Transaction value or ride date failed an integrity rule; source correction is required.' as issue_detail,
       true as blocks_stage3
from {{ ref('int_transaction_integrity') }} i
join {{ ref('int_transactions') }} t on t.occurrence_ids=i.occurrence_ids
cross join unnest(i.integrity_issues) u(issue)

union all
select transaction_id, business_key, occurrence_ids, amount_brl,
       'email_link_' || coalesce(email_link_status, 'missing') as issue_code, 'needs_client' as dq_bucket,
       case when email_link_status='ambiguous' then 'Observed email maps to multiple internal user IDs; do not choose by name or Employee ID.'
            when lower(coalesce(program,'')) like '%uber central%' and requester_email is null then 'Uber Central guest has no parsed requester; responsibility cannot be attributed.'
            else 'No unique internal user match for the effective rider/requester email.' end as issue_detail,
       true as blocks_stage3
from {{ ref('int_transaction_enrichment') }}
where (lower(coalesce(program,'')) like '%uber central%' and (requester_email is null or email_link_status is distinct from 'linked'))
   or (lower(coalesce(program,'')) not like '%uber central%' and (email is null or email_link_status is distinct from 'linked'))

union all
select transaction_id, business_key, occurrence_ids, amount_brl,
       'internal_user_not_active' as issue_code, 'rule_based' as dq_bucket,
       'Directory user is inactive, suspended, or has duplicate user records; matched address alone is not payment eligibility.' as issue_detail,
       true as blocks_stage3
from {{ ref('int_transaction_enrichment') }} where linked_user_status is distinct from 'active' and linked_user_id is not null

union all
select transaction_id, business_key, occurrence_ids, amount_brl,
       'employee_link_' || coalesce(employee_link_status, 'missing') as issue_code, 'rule_based' as dq_bucket,
       'Unique directory identity does not resolve to one active HR employee by matrícula.' as issue_detail,
       true as blocks_stage3
from {{ ref('int_transaction_enrichment') }} where employee_link_status is distinct from 'linked' and linked_user_id is not null

union all
select transaction_id, business_key, occurrence_ids, amount_brl,
       'employee_cpf_' || coalesce(employee_cpf_status, 'missing') as issue_code, 'rule_based' as dq_bucket,
       'Employee CPF is absent, invalid by check digits, or ambiguous in the HR master.' as issue_detail,
       payment_route_status='employee_reimbursement_candidate' as blocks_stage3
from {{ ref('int_transaction_enrichment') }}
where employee_cpf_status is distinct from 'valid' and linked_user_id is not null

union all
select transaction_id, business_key, occurrence_ids, amount_brl,
       'official_cost_center_' || coalesce(official_cost_center_status, 'missing') as issue_code, 'rule_based' as dq_bucket,
       'HR cost center is missing, absent from the registry, ambiguous, or inactive; directory CC is not promoted.' as issue_detail,
       true as blocks_stage3
from {{ ref('int_transaction_enrichment') }} where official_cost_center_status is distinct from 'active' and linked_user_id is not null

union all
select transaction_id, business_key, occurrence_ids, amount_brl,
       'directory_cost_center_mismatch' as issue_code, 'auto_fixable' as dq_bucket,
       'Used the HR cost center of record; the directory cost center remains in lineage for correction.' as issue_detail,
       false as blocks_stage3
from {{ ref('int_transaction_enrichment') }} where directory_cost_center_mismatch

union all
select transaction_id, business_key, occurrence_ids, amount_brl,
       'expense_code_' || expense_code_mapping_status as issue_code, 'needs_client' as dq_bucket,
       'Expense Code is missing, unmapped, or maps ambiguously; request an authoritative code mapping.' as issue_detail,
       true as blocks_stage3
from {{ ref('int_transaction_enrichment') }} where expense_code_mapping_status <> 'mapped'

union all
select transaction_id, business_key, occurrence_ids, amount_brl,
       'accounting_' || accounting_account_validation_status as issue_code, 'rule_based' as dq_bucket,
       'Mapped accounting account is missing, ambiguous, or not postable.' as issue_detail, true as blocks_stage3
from {{ ref('int_transaction_enrichment') }} where accounting_account_validation_status not in ('postable','not_checked')

union all
select transaction_id, business_key, occurrence_ids, amount_brl,
       'crosswalk_' || official_crosswalk_validation_status as issue_code, 'needs_client' as dq_bucket,
       'Official accounting-to-managerial crosswalk is missing or ambiguous; do not substitute the suggested managerial account.' as issue_detail,
       true as blocks_stage3
from {{ ref('int_transaction_enrichment') }} where official_crosswalk_validation_status not in ('mapped','not_checked')

union all
select transaction_id, business_key, occurrence_ids, amount_brl,
       'managerial_' || managerial_account_validation_status as issue_code, 'rule_based' as dq_bucket,
       'Official managerial account is missing, ambiguous, or not postable.' as issue_detail, true as blocks_stage3
from {{ ref('int_transaction_enrichment') }} where managerial_account_validation_status not in ('postable','not_checked')

union all
select transaction_id, business_key, occurrence_ids, amount_brl,
       'managerial_suggestion_disagrees_with_official_crosswalk' as issue_code, 'needs_client' as dq_bucket,
       'The expense mapping suggestion disagrees with the official crosswalk; no suggested value was used.' as issue_detail,
       true as blocks_stage3
from {{ ref('int_transaction_enrichment') }} where managerial_suggestion_status='suggestion_disagrees_with_official_crosswalk'

union all
select transaction_id, business_key, occurrence_ids, amount_brl,
       'financial_amount_' || amount_status as issue_code,
       case when amount_status='parse_failed' then 'rule_based' else 'needs_client' end as dq_bucket,
       'BRL amount is missing, disputed, or failed parsing; no value was imputed from a statement total or another field.' as issue_detail,
       true as blocks_stage3
from {{ ref('int_transaction_enrichment') }} where amount_status <> 'known'

union all
select transaction_id, business_key, occurrence_ids, amount_brl,
       'payment_route_' || payment_route_status as issue_code,
       case when payment_route_status like 'needs_client%' then 'needs_client' else 'rule_based' end as dq_bucket,
       case when payment_route_status='needs_client_card_destination' then 'Corporate card whose registry type is a PJ-account debit card; its destination in the payable process is not decided.'
            when payment_route_status='needs_client_card_activity_check' then 'Registry note reports the corporate card as cancelled; verify validity for this period.'
            when payment_route_status='needs_client_corporate_card_type_unmapped' then 'Card is in the corporate registry but its type has no configured route; not treated as personal reimbursement.'
            when payment_route_status='excluded_corporate_card_statement' then 'Corporate credit card is handled by its own card-statement process and is excluded from Uber AP.'
            else 'Payment method does not support a safe automatic payable route.' end as issue_detail,
       payment_route_status not in ('excluded_corporate_card_statement') as blocks_stage3
from {{ ref('int_transaction_enrichment') }}
where payment_route_status not in ('company_billed','employee_reimbursement_candidate')

union all
select transaction_id, business_key, occurrence_ids, amount_brl,
       'local_month_boundary_ambiguous' as issue_code, 'needs_client' as dq_bucket,
       'Request-local and drop-off-local timestamps fall in different months. Request month is retained as a candidate only; confirm reimbursement competence.' as issue_detail,
       true as blocks_stage3
from {{ ref('int_transaction_enrichment') }} where local_month_boundary_ambiguous and payment_route_status='employee_reimbursement_candidate'

union all
select transaction_id, business_key, occurrence_ids, amount_brl,
       'ride_' || employment_at_ride_status as issue_code, 'needs_client' as dq_bucket,
       'Ride date lies outside the employee admission/termination interval; HR must review access and historical status.' as issue_detail,
       true as blocks_stage3
from {{ ref('int_transaction_enrichment') }}
where employment_at_ride_status in ('after_termination','before_admission')

union all
select transaction_id, business_key, occurrence_ids, amount_brl,
       'local_competence_missing' as issue_code, 'needs_client' as dq_bucket,
       'No request-local timestamp is available to establish reimbursement month.' as issue_detail,
       true as blocks_stage3
from {{ ref('int_transaction_enrichment') }} where payment_route_status='employee_reimbursement_candidate' and reimbursement_competence_local is null

union all
select transaction_id, business_key, occurrence_ids, amount_brl,
       'admin_fee_allocation_rule_pending' as issue_code, 'needs_client' as dq_bucket,
       'Client has not specified the Expense Code/cost-center allocation rule for Admin Fee.' as issue_detail,
       true as blocks_stage3
from {{ ref('int_transaction_enrichment') }} where transaction_type='Admin Fee'

union all
select transaction_id, business_key, occurrence_ids, amount_brl,
       'mobility_eats_order_cap_violation' as issue_code, 'rule_based' as dq_bucket,
       'The known net Uber Eats order exceeds the R$ 80 policy cap; notify HR/manager without changing the Uber amount owed.' as issue_detail,
       false as blocks_stage3
from {{ ref('compliance_transaction_flags') }} where eats_order_cap_assessment='policy_violation_eats_order_cap'

union all
select transaction_id, business_key, occurrence_ids, amount_brl,
       'eats_order_cap_not_assessable' as issue_code, 'needs_client' as dq_bucket,
       'The Uber Eats order has unresolved value or more than one Fare; confirm the order total.' as issue_detail,
       false as blocks_stage3
from {{ ref('compliance_transaction_flags') }} where eats_order_cap_assessment='not_assessable_incomplete_order'

union all
select transaction_id, business_key, occurrence_ids, amount_brl,
       'mobility_weekend_policy_violation' as issue_code, 'rule_based' as dq_bucket,
       'Weekend trip is outside the two policy-permitted programs; routed to HR/manager without changing amount owed to Uber.' as issue_detail,
       false as blocks_stage3
from {{ ref('compliance_transaction_flags') }}
where weekend_policy_status='policy_violation_weekend_program'

union all
select transaction_id, business_key, occurrence_ids, amount_brl,
       'mobility_black_policy_violation' as issue_code, 'rule_based' as dq_bucket,
       'Uber Black is outside the Directors cost center (CC101); routed to HR/manager without changing amount owed to Uber.' as issue_detail,
       false as blocks_stage3
from {{ ref('compliance_transaction_flags') }}
where black_service_policy_status='policy_violation_black_outside_directors'

union all
select transaction_id, business_key, occurrence_ids, amount_brl,
       'mobility_eats_program_violation' as issue_code, 'rule_based' as dq_bucket,
       'Uber Eats is outside the Refeicao Hora Extra program; routed to HR/manager without changing amount owed to Uber.' as issue_detail,
       false as blocks_stage3
from {{ ref('compliance_transaction_flags') }}
where eats_program_policy_status='policy_violation_eats_program'
