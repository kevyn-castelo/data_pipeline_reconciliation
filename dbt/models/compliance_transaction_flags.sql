{{ config(materialized='table') }}

with local_dates as (
  select e.*,
         coalesce(e.dropoff_ts_local, e.request_ts_local) as assessed_local_ride_ts,
         (lower(coalesce(e.service,'')) like '%black%') as is_black_service,
         (lower(coalesce(e.service,'')) like '%eats%') as is_eats_service,
         (e.transaction_type='Admin Fee') as is_admin_fee
  from {{ ref('int_transaction_enrichment') }} e
)
select local_dates.transaction_id, local_dates.business_key, local_dates.occurrence_ids,
       local_dates.amount_brl, local_dates.service, local_dates.program,
       assessed_local_ride_ts,
       case when transaction_type<>'Fare' then 'not_applicable_non_fare_component'
            when list_contains(coalesce(i.integrity_issues,[]::varchar[]),'ride_after_report_date') then 'not_assessable_invalid_ride_date'
            when assessed_local_ride_ts is null then 'not_assessable_local_timestamp_missing'
            when dayofweek(assessed_local_ride_ts) in (0,6) and coalesce(upper(trim(program)),'') not in ('TRANSPORTE TURNO NOTURNO','REFEICAO HORA EXTRA') then 'policy_violation_weekend_program'
            when dayofweek(assessed_local_ride_ts) in (0,6) then 'weekend_program_allowed'
            else 'no_weekend_violation_detected' end as weekend_policy_status,
       case when not is_black_service or transaction_type<>'Fare' then 'not_applicable'
            when official_cost_center is null then 'not_assessable_cost_center_missing'
            when official_cost_center='CC101' then 'allowed_directors_cost_center'
            else 'policy_violation_black_outside_directors' end as black_service_policy_status,
       case when not is_eats_service then 'not_applicable'
            when upper(coalesce(program,''))='REFEICAO HORA EXTRA' then 'program_allowed_order_cap_not_assessed'
            else 'policy_violation_eats_program' end as eats_program_policy_status,
       case when not is_eats_service then 'not_applicable'
            when transaction_type<>'Fare' then 'assessed_on_fare_row_only'
            when o.unresolved_amount_count>0 or o.fare_count<>1 then 'not_assessable_incomplete_order'
            when o.known_order_total>80 then 'policy_violation_eats_order_cap'
            else 'within_eats_order_cap' end as eats_order_cap_assessment,
       case when is_admin_fee then 'needs_client_admin_fee_allocation_rule' else 'not_applicable' end as admin_fee_allocation_assessment,
       'holiday_not_assessed_no_client_calendar' as holiday_assessment,
       'compliance_flags_do_not_change_uber_amount_due' as financial_effect
from local_dates
left join {{ ref('int_eats_orders') }} o using(trip_id)
left join {{ ref('int_transaction_integrity') }} i using(occurrence_ids)
