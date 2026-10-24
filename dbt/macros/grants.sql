{#
    BI tools read the marts through a read-only role. Each mart model grants
    it SELECT (see dbt_project.yml); this on-run-end hook grants USAGE on the
    schema, which dbt's grants config does not manage. The schema check lets
    runs that do not build any mart (e.g. --select staging) finish cleanly.
#}
{% macro grant_schema_usage(schema, role) -%}
    do $$
    begin
        if exists (select 1 from pg_namespace where nspname = '{{ schema }}') then
            execute format('grant usage on schema %I to %I', '{{ schema }}', '{{ role }}');
        end if;
    end
    $$
{%- endmacro %}
