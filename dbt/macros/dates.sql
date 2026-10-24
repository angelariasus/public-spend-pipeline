{# Calendar date in Peru of a timestamptz; OCDS timestamps are stored in UTC. #}
{% macro to_lima_date(expression) -%}
    ({{ expression }} at time zone 'America/Lima')::date
{%- endmacro %}
