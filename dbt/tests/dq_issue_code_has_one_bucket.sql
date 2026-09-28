select issue_code, count(distinct dq_bucket) as bucket_count
from {{ ref('dq_report') }}
group by issue_code
having count(distinct dq_bucket) <> 1
