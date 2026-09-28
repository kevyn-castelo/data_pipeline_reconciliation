-- A released title belongs to a month that has ended and was issued on or before the as-of date.
select id_externo, competencia, data_emissao
from {{ ref('ap_titulos') }}
where last_day(strptime(competencia || '-01', '%Y-%m-%d'))::date >= cast('{{ var("as_of_date") }}' as date)
   or data_emissao > cast('{{ var("as_of_date") }}' as date)
