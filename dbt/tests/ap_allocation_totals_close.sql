-- Released titles must have lines, lines must add up to the title to the cent, and seq must be 1..n.
select t.id_externo, 'title_without_lines_or_not_closing' as failure
from {{ ref('ap_titulos') }} t
left join {{ ref('ap_rateios') }} r on r.id_externo_titulo=t.id_externo
group by t.id_externo, t.valor_total
having count(r.id_externo_titulo)=0 or count(r.valor)<>count(r.id_externo_titulo) or sum(r.valor) is distinct from t.valor_total
union all
select r.id_externo_titulo, 'orphan_rateio_line'
from {{ ref('ap_rateios') }} r
left join {{ ref('ap_titulos') }} t on t.id_externo=r.id_externo_titulo
where t.id_externo is null
union all
select id_externo_titulo, 'seq_not_1_to_n'
from {{ ref('ap_rateios') }}
group by id_externo_titulo
having min(seq)<>1 or max(seq)<>count(*) or count(distinct seq)<>count(*)
