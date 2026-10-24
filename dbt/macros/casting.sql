{#
    Defensive casts for text that comes straight from source CSVs.
    Values that do not match the expected format become NULL instead of
    failing the whole model; tests on the staging models catch unexpected
    NULL rates.
#}

{% macro to_numeric(expression) -%}
    case
        when {{ expression }} ~ '^-?[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?$'
            then ({{ expression }})::numeric
    end
{%- endmacro %}

{% macro to_integer(expression) -%}
    case
        when {{ expression }} ~ '^-?[0-9]+(\.0+)?$'
            then ({{ expression }})::numeric::bigint
    end
{%- endmacro %}

{# ISO 8601 with offset, e.g. 2026-10-23T10:44:12.886180-05:00 #}
{% macro to_timestamptz(expression) -%}
    case
        when {{ expression }} ~ '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}'
            then ({{ expression }})::timestamptz
    end
{%- endmacro %}

{# MEF timestamps, e.g. 2017-04-18 00:00:00 (local time, no offset) #}
{% macro to_local_timestamp(expression) -%}
    case
        when {{ expression }} ~ '^\d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2}(\.\d+)?)?$'
            then ({{ expression }})::timestamp
    end
{%- endmacro %}

{# MEF year-month codes, e.g. 201712 -> 2017-12-01 #}
{% macro yyyymm_to_date(expression) -%}
    case
        when {{ expression }} ~ '^\d{4}(0[1-9]|1[0-2])$'
            then to_date({{ expression }}, 'YYYYMM')
    end
{%- endmacro %}

{# Spanish yes/no flags: SI, SÍ, Sí, S�, NO #}
{% macro to_yes_no(expression) -%}
    case
        when upper({{ expression }}) like 'S%' then true
        when upper({{ expression }}) = 'NO' then false
    end
{%- endmacro %}

{% macro to_boolean(expression) -%}
    case
        when lower({{ expression }}) = 'true' then true
        when lower({{ expression }}) = 'false' then false
    end
{%- endmacro %}
