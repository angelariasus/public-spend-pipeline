-- Department where the investment project is located.
select
    coalesce(department, 'UNKNOWN') as department,
    sum(contracted_amount_pen) / 1e6 as contracted_millions_pen
from marts.mart_investment_vs_procurement
where is_matched_in_mef
group by department
order by contracted_millions_pen desc
