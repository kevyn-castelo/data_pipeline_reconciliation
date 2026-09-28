{{ config(materialized='table') }}

{% set client_id = var('client_id', 'madeireira_parana') %}
{% set reimbursement_issue_rule = var('reimbursement_issue_date_rule', none) %}

with details as (
  select candidate_group_key, company_billing_competence_utc as competence,
         count(*) as component_count,
         count(*) filter (where not amount_known) as amount_unknown_count,
         count(*) filter (where is_quarantined) as quarantined_count,
         count(*) filter (where not allocation_dimensions_valid) as allocation_dimension_error_count,
         sum(amount_brl) filter (where amount_known) as known_component_subtotal,
         case when count(*) filter (where not amount_known)=0 then sum(amount_brl) end as detail_total,
         sum(case when array_length(component_blockers)>0 then 1 else 0 end) as blocked_component_count,
         list_sort(list_distinct(flatten(list(component_blockers)))) as detail_blockers,
         count(*) filter (where transaction_ts_utc is null) as detail_timestamp_missing_count
  from {{ ref('int_ap_component_candidates') }}
  where payment_route_status='company_billed'
  group by candidate_group_key, company_billing_competence_utc
), vendor_by_cnpj as (
  select regexp_replace(coalesce(cnpj_raw,''),'[^0-9]','','g') as cnpj_digits,
         count(*) as vendor_match_count,
         count(*) filter(where cnpj_valid is true) as valid_vendor_match_count,
         min(legal_name) as legal_name,
         min(cnpj_valid) as cnpj_valid,
         min(source_file) as vendor_source_file,
         min(source_sheet) as vendor_source_sheet,
         min(source_row) as vendor_source_row,
         min(file_sha256) as vendor_file_sha256
  from {{ source('raw','raw_ref_vendors') }}
  where nullif(regexp_replace(coalesce(cnpj_raw,''),'[^0-9]','','g'),'') is not null
  group by 1
), statement_rows as (
  -- A re-sent statement (same number, same comparable content) is one document; divergent content is a conflict.
  select s.*,
         md5(concat_ws('|', coalesce(issuer_cnpj_digits,'<NULL>'), coalesce(cast(period_start as varchar),'<NULL>'),
             coalesce(cast(period_end as varchar),'<NULL>'), coalesce(cast(availability_date as varchar),'<NULL>'),
             coalesce(cast(issue_date as varchar),'<NULL>'), coalesce(cast(due_date as varchar),'<NULL>'),
             coalesce(payment_method,'<NULL>'), coalesce(cast(user_charges as varchar),'<NULL>'),
             coalesce(cast(service_fees as varchar),'<NULL>'), coalesce(cast(statement_total as varchar),'<NULL>'))) as statement_content_hash,
         row_number() over (partition by statement_number order by source_file, source_sheet nulls first, source_row) as statement_rank
  from {{ ref('stg_uber_statements') }} s
), statements as (
  select r.*, v.statement_occurrence_count, v.statement_version_count
  from statement_rows r
  join (select statement_number, count(*) as statement_occurrence_count,
               count(distinct statement_content_hash) as statement_version_count
        from statement_rows group by statement_number) v
    on v.statement_number is not distinct from r.statement_number
  where r.statement_rank=1
), statement_counts as (
  select competence, count(*) as statement_count
  from statements
  group by competence
), invoice_base as (
  select s.*, coalesce(sc.statement_count,0) as statement_count_for_period,
         coalesce(d.component_count,0) as component_count,
         coalesce(d.amount_unknown_count,0) as amount_unknown_count,
         coalesce(d.quarantined_count,0) as quarantined_count,
         coalesce(d.allocation_dimension_error_count,0) as allocation_dimension_error_count,
         d.known_component_subtotal, d.detail_total,
         coalesce(d.blocked_component_count,0) as blocked_component_count,
         coalesce(d.detail_blockers, []::varchar[]) as detail_blockers,
         coalesce(d.detail_timestamp_missing_count,0) as detail_timestamp_missing_count,
         coalesce(v.vendor_match_count,0) as vendor_match_count,
         coalesce(v.valid_vendor_match_count,0) as valid_vendor_match_count,
         v.legal_name as vendor_name, v.cnpj_valid as vendor_cnpj_valid,
         v.vendor_source_file, v.vendor_source_sheet, v.vendor_source_row, v.vendor_file_sha256
  from statements s
  left join statement_counts sc on sc.competence is not distinct from s.competence
  -- Detail attaches to a statement only when it is the single statement of its month; no precedence between documents.
  left join details d on d.competence is not distinct from s.competence and sc.statement_count=1
  left join vendor_by_cnpj v on v.cnpj_digits=s.issuer_cnpj_digits
), invoice_candidates as (
  select 'UBERAP-' || substr(sha256('{{ client_id }}|invoice|' || coalesce(statement_number,'MISSING') || '|' || coalesce(competence,'UNASSIGNED')),1,32) as id_externo,
         'FATURA_FORNECEDOR' as tipo, 'PJ' as beneficiario_tipo,
         issuer_cnpj_digits as beneficiario_documento, vendor_name as beneficiario_nome,
         statement_number as num_documento, issue_date as data_emissao,
         case when issue_date is not null then 'statement:data_emissao' end as issue_date_basis,
         due_date as data_vencimento, competence,
         -- A representative source row is not an approved financial version when documents conflict.
         case when statement_version_count=1 then statement_total end as valor_total_candidato,
         known_component_subtotal,
         case when statement_version_count=1 then statement_total end as statement_total,
         detail_total,
         case when statement_version_count=1 then user_charges end as user_charges,
         case when statement_version_count=1 then service_fees end as service_fees,
         availability_date,
         source_file as document_source_file, source_sheet as document_source_sheet,
         source_row as document_source_row, source_line_start as document_source_line_start,
         source_line_end as document_source_line_end, file_sha256 as document_file_sha256,
         statement_occurrence_count, statement_version_count,
         vendor_source_file, vendor_source_sheet, vendor_source_row, vendor_file_sha256,
         case when statement_count_for_period=1 then 'statement-month:' || coalesce(competence,'UNASSIGNED')
              else 'statement:' || coalesce(statement_number,'MISSING') end as candidate_group_key,
         component_count, amount_unknown_count, quarantined_count, allocation_dimension_error_count,
         payment_method,
         list_sort(list_distinct(list_concat(
           list_filter([
             case when nullif(trim(statement_number),'') is null then 'statement_number_missing' end,
             case when statement_version_count>1 then 'statement_versions_conflict' end,
             case when issuer_cnpj_digits is null or length(issuer_cnpj_digits)<>14 then 'issuer_cnpj_missing_or_malformed' end,
             case when vendor_match_count=0 then 'vendor_not_found_by_statement_cnpj' end,
             case when vendor_match_count<>1 then 'vendor_cnpj_ambiguous' end,
             case when valid_vendor_match_count<>1 or vendor_cnpj_valid is not true then 'vendor_cnpj_invalid' end,
             case when period_start is null or period_end is null or period_is_full_month is not true then 'statement_period_not_a_complete_calendar_month' end,
             case when period_is_single_month is not true then 'statement_period_spans_multiple_months' end,
             case when issue_date is null then 'issue_date_missing_or_invalid_in_source' end,
             case when due_date is null then 'due_date_missing_or_invalid' end,
             case when payment_method is distinct from 'Boleto' then 'statement_payment_method_not_boleto' end,
             case when statement_total is null or total_text_valid is not true or user_charges_text_valid is not true or service_fees_text_valid is not true then 'statement_amount_missing_invalid_or_over_precision' end,
             case when statement_components_close is not true then 'statement_components_do_not_close' end,
             case when statement_total_positive is not true then 'statement_total_not_positive' end,
             case when statement_count_for_period<>1 then 'statement_count_for_period_not_one' end,
             case when component_count=0 then 'periodic_billing_detail_missing' end,
             case when amount_unknown_count>0 then 'periodic_billing_detail_has_unknown_amount' end,
             case when quarantined_count>0 then 'periodic_billing_detail_has_quarantined_candidate' end,
             case when blocked_component_count>0 then 'periodic_billing_detail_has_blocked_component' end,
             case when detail_timestamp_missing_count>0 then 'periodic_billing_detail_timestamp_missing' end,
             case when statement_version_count=1 and detail_total is not null and statement_total is distinct from detail_total then 'statement_total_does_not_match_periodic_detail' end
           ], x -> x is not null), coalesce(detail_blockers,[]::varchar[])))) as release_blockers
  from invoice_base
), reimbursement_groups as (
  select candidate_group_key,
         min(linked_employee_number) as employee_number,
         min(beneficiary_cpf) as beneficiary_cpf,
         min(beneficiary_employee_name) as beneficiary_name,
         min(hr_employee_row_count) as hr_employee_row_count,
         min(beneficiary_cpf_valid) as beneficiary_cpf_valid,
         min(reimbursement_competence_local) as competence,
         count(*) as component_count,
         count(*) filter(where not amount_known) as amount_unknown_count,
         count(*) filter(where is_quarantined) as quarantined_count,
         count(*) filter(where not allocation_dimensions_valid) as allocation_dimension_error_count,
         sum(amount_brl) filter(where amount_known) as known_component_subtotal,
         case when count(*) filter(where not amount_known)=0 then sum(amount_brl) end as detail_total,
         sum(case when array_length(component_blockers)>0 then 1 else 0 end) as blocked_component_count,
         list_sort(list_distinct(flatten(list(component_blockers)))) as detail_blockers
  from {{ ref('int_ap_component_candidates') }}
  where payment_route_status='employee_reimbursement_candidate'
  group by candidate_group_key
), reimbursement_candidates as (
  select 'UBERAP-' || substr(sha256('{{ client_id }}|reimbursement|' || candidate_group_key),1,32) as id_externo,
         'REEMBOLSO_COLABORADOR' as tipo, 'PF' as beneficiario_tipo,
         beneficiary_cpf as beneficiario_documento, beneficiary_name as beneficiario_nome,
         -- Operational premise configured for this case (no reimbursement document exists in the sources);
         -- stays a client confirmation item in the controller summary.
         {% if reimbursement_issue_rule == 'last_day_of_competence_month' %}
         case when competence is not null then last_day(try_strptime(competence || '-01','%Y-%m-%d'))::date end as data_emissao,
         'config:last_day_of_competence_month' as issue_date_basis,
         {% else %}
         cast(null as date) as data_emissao,
         cast(null as varchar) as issue_date_basis,
         {% endif %}
         case when competence is not null then (try_strptime(competence || '-01','%Y-%m-%d') + interval '1 month' + interval '14 days')::date end as data_vencimento,
         competence,
         case when amount_unknown_count=0 then detail_total end as valor_total_candidato,
         known_component_subtotal, detail_total,
         candidate_group_key,
         component_count, amount_unknown_count, quarantined_count, allocation_dimension_error_count,
         'PIX' as payment_method,
         list_sort(list_distinct(list_concat(
           list_filter([
             case when employee_number is null then 'employee_identity_missing' end,
             case when hr_employee_row_count<>1 then 'hr_employee_not_unique' end,
             case when beneficiary_cpf_valid is not true or beneficiary_cpf is null or length(beneficiary_cpf)<>11 then 'beneficiary_cpf_invalid_or_missing' end,
             case when competence is null then 'reimbursement_competence_missing' end,
             {% if reimbursement_issue_rule != 'last_day_of_competence_month' %}'needs_client_reimbursement_issue_date_rule',{% endif %}
             case when amount_unknown_count>0 then 'reimbursement_detail_has_unknown_amount' end,
             case when quarantined_count>0 then 'reimbursement_detail_has_quarantined_candidate' end,
             case when blocked_component_count>0 then 'reimbursement_detail_has_blocked_component' end,
             case when detail_total is not null and detail_total<=0 then 'reimbursement_total_not_positive' end
           ], x -> x is not null), coalesce(detail_blockers,[]::varchar[])))) as release_blockers
  from reimbursement_groups
), month_candidates as (
  -- Company-billed detail for a month with zero or several statements: one held candidate per month,
  -- so every component belongs to exactly one title candidate without choosing between documents.
  select d.*, coalesce(sc.statement_count,0) as statement_count_for_period
  from details d
  left join statement_counts sc on sc.competence is not distinct from d.competence
  where coalesce(sc.statement_count,0) <> 1
), month_level_candidates as (
  select 'UBERAP-' || substr(sha256('{{ client_id }}|' || case when statement_count_for_period=0 then 'missing-statement' else 'multiple-statements' end || '|' || candidate_group_key),1,32) as id_externo,
         'FATURA_FORNECEDOR' as tipo, 'PJ' as beneficiario_tipo, competence,
         case when amount_unknown_count=0 then detail_total end as valor_total_candidato,
         known_component_subtotal, detail_total,
         candidate_group_key, component_count, amount_unknown_count, quarantined_count,
         allocation_dimension_error_count,
         list_sort(list_distinct(list_concat(
           [case when statement_count_for_period=0 then 'monthly_statement_missing' else 'multiple_statements_for_period' end],
           coalesce(detail_blockers,[]::varchar[])))) as release_blockers
  from month_candidates
)
select *, (array_length(release_blockers)=0) as preliminary_header_clear,
       case when array_length(release_blockers)=0 then 'header_checks_clear' else 'held' end as preliminary_status
from (
  select * from invoice_candidates
  union all by name select * from reimbursement_candidates
  union all by name select * from month_level_candidates
)
