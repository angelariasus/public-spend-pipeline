{{ config(indexes=[{'columns': ['date_day'], 'unique': true}]) }}

-- MEF dates go back to 2001; OECE dates cover the loaded periods.
with days as (
    {{ dbt_utils.date_spine(
        datepart="day",
        start_date="cast('2000-01-01' as date)",
        end_date="cast('2031-01-01' as date)"
    ) }}
)

select
    date_day::date as date_day,
    extract(year from date_day)::int as calendar_year,
    extract(quarter from date_day)::int as calendar_quarter,
    extract(month from date_day)::int as calendar_month,
    to_char(date_day, 'YYYY-MM') as calendar_year_month,
    date_trunc('month', date_day)::date as month_start,
    to_char(date_day, 'FMMonth') as month_name,
    extract(isodow from date_day)::int as iso_day_of_week,
    extract(isodow from date_day) in (6, 7) as is_weekend
from days
