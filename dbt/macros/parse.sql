{% macro norm_card_brand(expr) -%}
case when regexp_replace(upper(coalesce({{ expr }}, '')), '[^A-Z0-9]', '', 'g') in ('AMEX','AMERICANEXPRESS') then 'AMERICANEXPRESS'
     else nullif(regexp_replace(upper(coalesce({{ expr }}, '')), '[^A-Z0-9]', '', 'g'), '') end
{%- endmacro %}

{% macro rv(field) -%}json_extract_string(canonical_values, '$.{{ field }}'){%- endmacro %}

{% macro raw_available(field) -%}
{% if field == 'request_ts_utc' %}json_exists(canonical_values, '$.request_date_utc') and json_exists(canonical_values, '$.request_time_utc')
{% elif field == 'request_ts_local' %}json_exists(canonical_values, '$.request_date_local') and json_exists(canonical_values, '$.request_time_local')
{% elif field == 'dropoff_ts_utc' %}json_exists(canonical_values, '$.dropoff_date_utc') and json_exists(canonical_values, '$.dropoff_time_utc')
{% elif field == 'dropoff_ts_local' %}json_exists(canonical_values, '$.dropoff_date_local') and json_exists(canonical_values, '$.dropoff_time_local')
{% elif field == 'request_utc_offset_min' %}json_exists(canonical_values, '$.request_utc_offset')
{% elif field == 'requester_email' %}json_exists(canonical_values, '$.requester')
{% elif field in ['card_brand', 'card_last4'] %}json_exists(canonical_values, '$.payment_method_raw')
{% else %}json_exists(canonical_values, '$.{{ field }}')
{% endif %}
{%- endmacro %}

{% macro parsed_money(field) -%}
case
  when {{ rv(field) }} is null or trim({{ rv(field) }}) in ('', '--') then null
  when regexp_matches(trim({{ rv(field) }}), '^[+-]?[0-9]+$') then try_cast(trim({{ rv(field) }}) as decimal(15,2))
  when (file_format = 'xlsx' or decimal_separator = '.') and regexp_matches(trim({{ rv(field) }}), '^[+-]?[0-9]+[.][0-9]+$') then
    case
      when abs(try_cast(trim({{ rv(field) }}) as decimal(38,18)) - round(try_cast(trim({{ rv(field) }}) as decimal(38,18)), 2)) < 0.000001
      then try_cast(round(try_cast(trim({{ rv(field) }}) as decimal(38,18)), 2) as decimal(15,2))
      else null
    end
  when decimal_separator = ',' and regexp_matches(trim({{ rv(field) }}), '^[+-]?[0-9]+,[0-9]+$') then
    case
      when abs(try_cast(replace(trim({{ rv(field) }}), ',', '.') as decimal(38,18)) - round(try_cast(replace(trim({{ rv(field) }}), ',', '.') as decimal(38,18)), 2)) < 0.000001
      then try_cast(round(try_cast(replace(trim({{ rv(field) }}), ',', '.') as decimal(38,18)), 2) as decimal(15,2))
      else null
    end
  else null
end
{%- endmacro %}

{% macro try_file_format(raw_expr, format_key) -%}
case
{% for fmt in var('date_formats', []) %}
  when json_extract_string(date_formats_json, '$.date_formats.{{ format_key }}') = '{{ fmt }}' then try_strptime(trim({{ raw_expr }}), '{{ fmt }}')
{% endfor %}
  else null
end
{%- endmacro %}

{% macro parsed_ts(raw_expr, format_key, epoch_expr) -%}
case
  when {{ raw_expr }} is null or trim({{ raw_expr }}) = '' then null
  when regexp_matches(trim({{ raw_expr }}), '^[+-]?[0-9]+([.][0-9]+)?$') then
    (cast({{ epoch_expr }} as timestamp) +
      case
        when abs(try_cast(trim({{ raw_expr }}) as decimal(38,18)) * 86400 - floor(try_cast(trim({{ raw_expr }}) as decimal(38,18)) * 86400 + 0.5)) > 0
         and abs(try_cast(trim({{ raw_expr }}) as decimal(38,18)) * 86400 - floor(try_cast(trim({{ raw_expr }}) as decimal(38,18)) * 86400 + 0.5)) < 0.000001
        then floor(try_cast(trim({{ raw_expr }}) as decimal(38,18)) * 86400 + 0.5) / 86400
        else try_cast(trim({{ raw_expr }}) as decimal(38,18))
      end * interval '1 day')
  else {{ try_file_format(raw_expr, format_key) }}
end
{%- endmacro %}

{% macro parsed_datetime(date_field, time_field, format_key) -%}
case
  when regexp_matches(coalesce({{ rv(date_field) }}, ''), '^[0-9]+([.][0-9]+)?$') then
    {{ parsed_ts("cast(try_cast(" + rv(date_field) + " as decimal(38,18)) + try_cast(" + rv(time_field) + " as decimal(38,18)) as varchar)", format_key, 'workbook_epoch') }}
  else {{ try_file_format("trim(" + rv(date_field) + " || ' ' || " + rv(time_field) + ")", format_key) }}
end
{%- endmacro %}
