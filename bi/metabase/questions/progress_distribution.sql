-- Active projects with at least S/ 1M contracted, by reported physical progress.
with projects as (
    select
        case
            when physical_progress_pct is null then 0
            when physical_progress_pct < 25 then 1
            when physical_progress_pct < 50 then 2
            when physical_progress_pct < 75 then 3
            when physical_progress_pct < 100 then 4
            else 5
        end as bucket
    from marts.mart_investment_vs_procurement
    where
        not is_closed
        and contracted_amount_pen >= 1000000
)

select
    (array['not reported', '0-25%', '25-50%', '50-75%', '75-100%', '100% or more'])[bucket + 1]
        as physical_progress,
    count(*) as projects
from projects
group by bucket
order by bucket
