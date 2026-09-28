{{ config(materialized='table') }}

with cards as (
  select {{ norm_card_brand('card_brand') }} as card_brand_norm,
         trim(card_last4) as card_last4, count(*) as card_record_count,
         upper(trim(min(card_type))) as card_type, min(observation) as card_observation
  from {{ source('raw', 'raw_ref_corporate_cards') }}
  where nullif(trim(card_brand), '') is not null and nullif(trim(card_last4), '') is not null
  group by 1,2
), expense_map as (
  select upper(trim(expense_code)) as expense_code, count(*) as map_row_count,
         count(distinct coalesce(accounting_target_account, '<NULL>')) as account_target_count,
         count(distinct coalesce(managerial_suggested_account, '<NULL>')) as suggestion_count,
         min(accounting_target_account) as accounting_target_account,
         min(managerial_suggested_account) as managerial_suggested_account
  from {{ source('raw', 'raw_ref_expense_code_map') }}
  where nullif(trim(expense_code), '') is not null
  group by 1
), accounting as (
  select trim(account_code) as account_code, count(*) as account_row_count,
         count(distinct coalesce(accepts_posting, '<NULL>')) as posting_flag_count,
         min(accepts_posting) as accepts_posting,
         min(account_type) as account_type
  from {{ source('raw', 'raw_ref_accounting_accounts') }}
  where nullif(trim(account_code), '') is not null
  group by 1
), accounting_parents as (
  -- An account with sub-accounts is synthetic even if the chart flags it as postable.
  select distinct trim(p.account_code) as account_code
  from {{ source('raw', 'raw_ref_accounting_accounts') }} p
  join {{ source('raw', 'raw_ref_accounting_accounts') }} c on starts_with(trim(c.account_code), trim(p.account_code) || '.')
), crosswalk as (
  select trim(accounting_account) as accounting_account, count(*) as crosswalk_row_count,
         count(distinct coalesce(managerial_account, '<NULL>')) as managerial_target_count,
         min(managerial_account) as managerial_account
  from {{ source('raw', 'raw_ref_accounting_managerial_map') }}
  where nullif(trim(accounting_account), '') is not null
  group by 1
), managerial as (
  select trim(managerial_account) as managerial_account, count(*) as managerial_row_count,
         count(distinct coalesce(accepts_posting, '<NULL>')) as posting_flag_count,
         min(accepts_posting) as accepts_posting
  from {{ source('raw', 'raw_ref_managerial_accounts') }}
  where nullif(trim(managerial_account), '') is not null
  group by 1
), managerial_parents as (
  select distinct trim(p.managerial_account) as managerial_account
  from {{ source('raw', 'raw_ref_managerial_accounts') }} p
  join {{ source('raw', 'raw_ref_managerial_accounts') }} c on starts_with(trim(c.managerial_account), trim(p.managerial_account) || '.')
), classified as (
  select t.*,
         case when lower(coalesce(t.program,'')) like '%uber central%' then t.requester_email else t.email end as responsibility_email,
         case when lower(coalesce(t.program,'')) like '%uber central%' then r.email_link_status else u.email_link_status end as email_link_status,
         case when lower(coalesce(t.program,'')) like '%uber central%' then r.user_id else u.user_id end as linked_user_id,
         case when lower(coalesce(t.program,'')) like '%uber central%' then r.matched_by else u.matched_by end as email_link_method,
         case when lower(coalesce(t.program,'')) like '%uber central%' then r.user_status_check else u.user_status_check end as linked_user_status,
         case when lower(coalesce(t.program,'')) like '%uber central%' then r.employee_link_status else u.employee_link_status end as employee_link_status,
         case when lower(coalesce(t.program,'')) like '%uber central%' then r.employee_number else u.employee_number end as linked_employee_number,
         case when lower(coalesce(t.program,'')) like '%uber central%' then r.employee_name else u.employee_name end as linked_employee_name,
         case when lower(coalesce(t.program,'')) like '%uber central%' then r.employee_status else u.employee_status end as linked_employee_status,
         case when lower(coalesce(t.program,'')) like '%uber central%' then r.admission_date_raw else u.admission_date_raw end as admission_date_raw,
         case when lower(coalesce(t.program,'')) like '%uber central%' then r.termination_date_raw else u.termination_date_raw end as termination_date_raw,
         case when lower(coalesce(t.program,'')) like '%uber central%' then r.employee_cpf_status else u.employee_cpf_status end as employee_cpf_status,
         case when lower(coalesce(t.program,'')) like '%uber central%' then r.official_cost_center else u.official_cost_center end as official_cost_center,
         case when lower(coalesce(t.program,'')) like '%uber central%' then r.official_cost_center_status else u.official_cost_center_status end as official_cost_center_status,
         case when lower(coalesce(t.program,'')) like '%uber central%' then r.directory_cost_center_mismatch else u.directory_cost_center_mismatch end as directory_cost_center_mismatch,
         case when upper(coalesce(t.payment_method_raw,''))='PERIODIC BILLING' then 'company_statement'
              when c.card_record_count > 1 then 'corporate_card_ambiguous'
              when c.card_record_count = 1 then 'corporate_card'
              when t.card_brand is not null and t.card_last4 is not null then 'personal_card'
              else 'payment_method_unknown' end as payment_channel,
         case when upper(coalesce(t.payment_method_raw,''))='PERIODIC BILLING' then 'company_billed'
              when c.card_record_count > 1 then 'needs_client_card_registry_ambiguity'
              when c.card_record_count = 1 and lower(coalesce(c.card_observation,'')) like '%cancelado%' then 'needs_client_card_activity_check'
              {% for card_type, route in var('corporate_card_routes', {}).items() %}
              when c.card_record_count = 1 and c.card_type = '{{ card_type | upper }}' then '{{ route }}'
              {% endfor %}
              when c.card_record_count = 1 then 'needs_client_corporate_card_type_unmapped'
              when t.card_brand is not null and t.card_last4 is not null then 'employee_reimbursement_candidate'
              else 'payment_method_unknown' end as payment_route_status,
         c.card_type as corporate_card_type, c.card_observation as corporate_card_observation,
         m.map_row_count, m.account_target_count, m.accounting_target_account,
         m.managerial_suggested_account,
         a.account_row_count, a.account_type, a.accepts_posting as accounting_accepts_posting,
         x.crosswalk_row_count, x.managerial_target_count, x.managerial_account as official_managerial_account,
         g.managerial_row_count, g.accepts_posting as managerial_accepts_posting,
         case when t.expense_code is null then 'missing_expense_code' when m.expense_code is null then 'unmapped_expense_code'
              when m.account_target_count > 1 or m.suggestion_count > 1 then 'ambiguous_expense_mapping' else 'mapped' end as expense_code_mapping_status,
         case when m.expense_code is null or m.account_target_count <> 1 then 'not_checked'
              when m.accounting_target_account is null then 'missing_accounting_target'
              when a.account_code is null then 'accounting_account_not_found'
              when a.account_row_count > 1 or a.posting_flag_count > 1 then 'ambiguous_accounting_account'
              when upper(trim(a.accepts_posting)) not in ('S','SIM','TRUE','1') then 'account_not_postable'
              when ap.account_code is not null then 'account_synthetic'
              else 'postable' end as accounting_account_validation_status,
         case when m.expense_code is null or m.account_target_count <> 1 or m.accounting_target_account is null then 'not_checked'
              when x.accounting_account is null or x.managerial_target_count=0 then 'official_crosswalk_missing'
              when x.managerial_target_count > 1 then 'official_crosswalk_ambiguous'
              else 'mapped' end as official_crosswalk_validation_status,
         case when x.managerial_target_count <> 1 or x.managerial_account is null then 'not_checked'
              when g.managerial_account is null then 'managerial_account_not_found'
              when g.managerial_row_count > 1 or g.posting_flag_count > 1 then 'ambiguous_managerial_account'
              when upper(trim(g.accepts_posting)) not in ('S','SIM','TRUE','1') then 'managerial_account_not_postable'
              when gp.managerial_account is not null then 'managerial_account_synthetic'
              else 'postable' end as managerial_account_validation_status,
         case when m.managerial_suggested_account is null then 'not_provided'
              when x.managerial_target_count <> 1 or x.managerial_account is null then 'not_comparable'
              when m.managerial_suggested_account <> x.managerial_account then 'suggestion_disagrees_with_official_crosswalk'
              else 'agrees_with_official_crosswalk' end as managerial_suggestion_status,
         case when t.transaction_ts_utc is not null and upper(coalesce(t.payment_method_raw,''))='PERIODIC BILLING' then strftime(t.transaction_ts_utc, '%Y-%m') end as company_billing_competence_utc,
         case when c.card_record_count is null and t.card_brand is not null and t.card_last4 is not null then strftime(t.request_ts_local, '%Y-%m') end as reimbursement_competence_local,
         (t.request_ts_local is not null and t.dropoff_ts_local is not null and strftime(t.request_ts_local, '%Y-%m') <> strftime(t.dropoff_ts_local, '%Y-%m')) as local_month_boundary_ambiguous
  from {{ ref('int_transactions') }} t
  left join {{ ref('int_uber_email_links') }} u on u.email_norm=nullif(lower(trim(t.email)), '')
  left join {{ ref('int_requester_email_links') }} r on r.email_norm=nullif(lower(trim(t.requester_email)), '')
  left join cards c on c.card_brand_norm = {{ norm_card_brand('t.card_brand') }} and c.card_last4=t.card_last4
  left join expense_map m on m.expense_code=t.expense_code
  left join accounting a on a.account_code=m.accounting_target_account
  left join accounting_parents ap on ap.account_code=m.accounting_target_account
  left join crosswalk x on x.accounting_account=m.accounting_target_account
  left join managerial g on g.managerial_account=x.managerial_account
  left join managerial_parents gp on gp.managerial_account=x.managerial_account
), final_classification as (
  select classified.*,
         -- Custo × Despesa moves CMV and gross profit: codes awaiting a controller decision are always held,
         -- and a cost (Custo) account is accepted only in cost centers approved for it. A new cost center
         -- is held until approved, instead of passing silently.
         coalesce(list_contains([{% for code in var('classification_pending_expense_codes', []) %}'{{ code }}'{% if not loop.last %},{% endif %}{% endfor %}]::varchar[], expense_code)
                  or (upper(trim(account_type)) = 'CUSTO' and official_cost_center is not null
                      and not list_contains([{% for cc in var('cost_account_cost_centers', []) %}'{{ cc }}'{% if not loop.last %},{% endif %}{% endfor %}]::varchar[], official_cost_center)),
                  false) as cost_expense_review_required,
         case when linked_employee_number is null then 'not_assessable_employee_missing'
              when request_ts_local is null then 'not_assessable_ride_date_missing'
              when nullif(admission_date_raw,'') is null then 'not_assessable_admission_date_missing'
              when nullif(admission_date_raw,'') is not null and try_strptime(admission_date_raw,'%d/%m/%Y') is null then 'not_assessable_admission_date_invalid'
              when nullif(termination_date_raw,'') is not null and try_strptime(termination_date_raw,'%d/%m/%Y') is null then 'not_assessable_termination_date_invalid'
              when upper(trim(linked_employee_status)) is distinct from 'ATIVO' and nullif(termination_date_raw,'') is null then 'not_assessable_inactive_without_termination_date'
              when try_strptime(admission_date_raw,'%d/%m/%Y')::date > request_ts_local::date then 'before_admission'
              when try_strptime(termination_date_raw,'%d/%m/%Y')::date < request_ts_local::date then 'after_termination'
              else 'within_employment_period' end as employment_at_ride_status,
         case when expense_code_mapping_status <> 'mapped' then expense_code_mapping_status
              when accounting_account_validation_status <> 'postable' then accounting_account_validation_status
              when official_crosswalk_validation_status <> 'mapped' then official_crosswalk_validation_status
              when managerial_account_validation_status <> 'postable' then managerial_account_validation_status
              when managerial_suggestion_status='suggestion_disagrees_with_official_crosswalk' then managerial_suggestion_status
              else 'mapped_to_postable_accounts' end as expense_classification_status
  from classified
)
select *,
       case when payment_route_status='company_billed' then company_billing_competence_utc
            when payment_route_status='employee_reimbursement_candidate' then reimbursement_competence_local end as applicable_competence,
       case when is_quarantined then 'canonical_candidate_retained'
            when employment_at_ride_status='after_termination' then 'ride_after_termination'
            when employment_at_ride_status='before_admission' then 'ride_before_admission'
            when payment_route_status = 'excluded_corporate_card_statement' then payment_route_status
            when transaction_type='Admin Fee' then 'admin_fee_allocation_rule_pending'
            when amount_status <> 'known' then 'financial_amount_not_known'
            when email_link_status is distinct from 'linked' then coalesce(email_link_status,'email_or_requester_missing')
            when linked_user_status='ambiguous_user_record' then 'ambiguous_user_record'
            when employee_link_status is distinct from 'linked' then coalesce(employee_link_status,'employee_not_linked')
            when employment_at_ride_status is distinct from 'within_employment_period' then employment_at_ride_status
            when payment_route_status='employee_reimbursement_candidate' and upper(trim(linked_employee_status)) is distinct from 'ATIVO' then 'former_employee_reimbursement_review'
            when official_cost_center_status is distinct from 'active' then coalesce(official_cost_center_status,'official_cost_center_unavailable')
            when employee_cpf_status is distinct from 'valid' and payment_route_status='employee_reimbursement_candidate' then coalesce(employee_cpf_status,'employee_cpf_unavailable')
            when local_month_boundary_ambiguous and payment_route_status='employee_reimbursement_candidate' then 'local_month_boundary_ambiguous'
            when payment_route_status like 'needs_client%' then payment_route_status
            when cost_expense_review_required then 'cost_expense_classification_pending'
            when expense_code_mapping_status <> 'mapped' then expense_code_mapping_status
            when accounting_account_validation_status <> 'postable' then accounting_account_validation_status
            when official_crosswalk_validation_status <> 'mapped' then official_crosswalk_validation_status
            when managerial_account_validation_status <> 'postable' then managerial_account_validation_status
            when managerial_suggestion_status='suggestion_disagrees_with_official_crosswalk' then 'expense_classification_suggestion_disagreement'
            when payment_route_status='payment_method_unknown' then 'payment_method_unknown'
            when payment_route_status='employee_reimbursement_candidate' and reimbursement_competence_local is null then 'local_competence_missing'
            else 'candidate_for_stage3_review' end as stage3_financial_gate
from final_classification
