{#
    Like dbt's `relationships` test, for multi-column keys: every row of the
    model must match a row of `to` on all `columns` (paired with `to_columns`).
    Rows with a NULL in any key column are ignored.
#}
{% test composite_relationships(model, columns, to, to_columns) %}

select child.*
from {{ model }} as child
where
    {% for column in columns %}
        child.{{ column }} is not null{% if not loop.last %} and{% endif %}
    {% endfor %}
    and not exists (
        select 1
        from {{ to }} as parent
        where
            {% for column in columns %}
                parent.{{ to_columns[loop.index0] }} = child.{{ column }}
                {%- if not loop.last %} and{% endif %}
            {% endfor %}
    )

{% endtest %}
