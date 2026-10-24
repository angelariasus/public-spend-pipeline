{#
    Read a field from an OCDS raw row.
    ocds('awards/0/value/amount') -> data ->> 'compiledRelease/awards/0/value/amount'
    The "/0/" in child tables is a header template: each row is one element.
#}
{% macro ocds(path) -%}
    data ->> 'compiledRelease/{{ path }}'
{%- endmacro %}
