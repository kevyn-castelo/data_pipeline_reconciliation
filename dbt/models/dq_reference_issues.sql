{{ config(materialized='table') }}

select 'employees' as entity_name, source_file, source_sheet, source_row,
       'invalid_cpf' as issue_code, 'rule_based' as dq_bucket,
       'CPF fails length/repeated-digit/check-digit validation; reimbursement beneficiary must be held.' as issue_detail,
       true as blocks_stage3
from {{ source('raw', 'raw_ref_employees') }} where cpf_valid is not true

union all
select 'vendors' as entity_name, source_file, source_sheet, source_row,
       'invalid_cnpj' as issue_code, 'rule_based' as dq_bucket,
       'CNPJ fails length/repeated-digit/check-digit validation; do not use this vendor record for import.' as issue_detail,
       true as blocks_stage3
from {{ source('raw', 'raw_ref_vendors') }} where cnpj_valid is not true

union all
select 'vendors' as entity_name, source_file, source_sheet, source_row,
       'uber_vendor_name_multiple_candidates' as issue_code, 'needs_client' as dq_bucket,
       'Multiple vendor records match Uber legal name; confirm the intended supplier and valid CNPJ before payable creation.' as issue_detail,
       true as blocks_stage3
from {{ ref('int_uber_vendor_candidates') }} where same_name_candidate_count > 1

union all
select 'compliance_reference' as entity_name, null as source_file, null as source_sheet, null as source_row,
       'holiday_calendar_not_supplied' as issue_code, 'needs_client' as dq_bucket,
       'No client holiday calendar was supplied. Weekend checks ran; holiday checks were not inferred.' as issue_detail,
       false as blocks_stage3
