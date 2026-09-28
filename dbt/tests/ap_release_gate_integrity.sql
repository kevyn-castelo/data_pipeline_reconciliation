select id_externo
from {{ ref('int_ap_release_gate') }}
where is_released
  and (array_length(final_release_blockers)>0
       or valor_total_candidato is null or valor_total_candidato<=0
       or data_emissao is null or data_vencimento is null
       or beneficiario_documento is null or beneficiario_nome is null
       or allocation_line_count=0 or blocked_allocation_line_count>0
       or ready_allocation_total is distinct from valor_total_candidato)
