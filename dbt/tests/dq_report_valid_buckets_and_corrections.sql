select * from {{ ref('dq_report') }}
where dq_bucket not in ('auto_fixable','rule_based','needs_client')
   or (dq_bucket='auto_fixable' and
       (nullif(source_file,'') is null or source_row is null or nullif(before_value,'') is null or nullif(after_value,'') is null))
