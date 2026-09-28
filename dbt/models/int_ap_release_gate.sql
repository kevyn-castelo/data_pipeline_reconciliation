{{ config(materialized='table') }}

with line_totals as (
  select id_externo,
         count(*) as allocation_line_count,
         count(*) filter(where allocation_status<>'ready') as blocked_allocation_line_count,
         count(*) filter(where amount_unknown_count>0) as allocation_line_amount_unknown_count,
         sum(line_amount) filter(where allocation_status='ready') as ready_allocation_total
  from {{ ref('int_ap_allocation_candidates') }}
  group by id_externo
), combined as (
  select t.*, i.status as issued_status, i.valor_total as issued_value,
         coalesce(l.allocation_line_count,0) as allocation_line_count,
         coalesce(l.blocked_allocation_line_count,0) as blocked_allocation_line_count,
         coalesce(l.allocation_line_amount_unknown_count,0) as allocation_line_amount_unknown_count,
         l.ready_allocation_total
  from {{ ref('int_ap_title_candidates') }} t
  left join line_totals l using(id_externo)
  left join {{ source('raw','raw_issued_titles') }} i using(id_externo)
), final as (
  select *,
         list_sort(list_distinct(list_concat(release_blockers,
           list_filter([
             case when valor_total_candidato is null then 'payable_total_unavailable' end,
             case when valor_total_candidato is not null and valor_total_candidato<=0 then 'payable_total_not_positive' end,
             case when length(id_externo)>80 then 'id_externo_exceeds_layout_length' end,
             case when beneficiario_documento is null or (beneficiario_tipo='PJ' and length(beneficiario_documento)<>14) or (beneficiario_tipo='PF' and length(beneficiario_documento)<>11) then 'beneficiary_document_missing_or_wrong_length' end,
             case when beneficiario_nome is null or trim(beneficiario_nome)='' or length(beneficiario_nome)>120 then 'beneficiary_name_missing_or_exceeds_layout_length' end,
             case when tipo='FATURA_FORNECEDOR' and (num_documento is null or trim(num_documento)='' or length(num_documento)>40) then 'invoice_document_missing_or_exceeds_layout_length' end,
             case when competence is null or not regexp_matches(competence,'^[0-9]{4}-[0-9]{2}$') then 'competence_missing_or_invalid' end,
             case when competence is not null and competence < '{{ var("first_automated_competence") }}' then 'competence_before_automation_start' end,
             case when issued_status is not null then 'title_already_issued_immutable' end,
             case when issued_status is not null and valor_total_candidato is distinct from issued_value then 'issued_title_value_changed_adjustment_required' end,
             case when data_emissao is null then 'issue_date_missing' end,
             case when data_vencimento is null then 'due_date_missing' end,
             case when data_vencimento is not null and data_vencimento < cast('{{ var("as_of_date") }}' as date) then 'due_date_in_past' end,
             case when allocation_line_count=0 then 'allocation_lines_missing' end,
             case when blocked_allocation_line_count>0 then 'allocation_line_components_blocked' end,
             case when allocation_line_amount_unknown_count>0 then 'allocation_line_amount_unknown' end,
             case when valor_total_candidato is not null and ready_allocation_total is distinct from valor_total_candidato then 'allocation_total_does_not_close_to_payable' end
           ], x -> x is not null)))) as final_release_blockers
  from combined
)
select *, (array_length(final_release_blockers)=0) as is_released
from final
