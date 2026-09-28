-- Every payable component belongs to exactly one title candidate (no gaps, no double counting).
select c.transaction_id, c.occurrence_ids, count(t.id_externo) as title_candidates
from {{ ref('int_ap_component_candidates') }} c
left join {{ ref('int_ap_title_candidates') }} t using(candidate_group_key)
group by c.transaction_id, c.occurrence_ids
having count(t.id_externo) <> 1
