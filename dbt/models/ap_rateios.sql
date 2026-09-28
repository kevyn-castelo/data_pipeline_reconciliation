{{ config(materialized='view') }}
select l.id_externo as id_externo_titulo, l.seq, l.conta_contabil, l.conta_gerencial,
       l.centro_custo, l.line_amount::decimal(15,2) as valor,
       t.competence as competencia,
       case when t.tipo='FATURA_FORNECEDOR' then 'Rateio Uber demonstrativo ' || t.num_documento
            else 'Reembolso Uber ' || t.beneficiario_nome || ' ' || t.competence end as historico
from {{ ref('int_ap_allocation_candidates') }} l
join {{ ref('int_ap_release_gate') }} t using(id_externo)
where t.is_released and l.allocation_status='ready'
