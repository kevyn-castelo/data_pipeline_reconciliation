select id_externo, count(*) as n
from {{ ref('int_ap_title_candidates') }}
group by id_externo
having id_externo is null or count(*)<>1
