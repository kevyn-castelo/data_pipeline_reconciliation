{{ config(materialized='view') }}
select id_externo, tipo, beneficiario_tipo, beneficiario_documento, beneficiario_nome,
       num_documento, data_emissao, data_vencimento, competence as competencia,
       valor_total_candidato::decimal(15,2) as valor_total,
       'BRL' as moeda,
       case when tipo='FATURA_FORNECEDOR' then 'Uber demonstrativo ' || num_documento
            else 'Reembolso Uber ' || beneficiario_nome || ' ' || competencia end as historico,
       'UBER_BUSINESS_ALCHEMY' as origem
from {{ ref('int_ap_release_gate') }}
where is_released
