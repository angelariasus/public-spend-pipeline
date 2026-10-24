select
    dates.month_start,
    awards.main_procurement_category as category,
    sum(awards.award_amount_pen) / 1e6 as awarded_millions_pen
from marts.fct_award as awards
inner join marts.dim_date as dates
    on awards.awarded_on = dates.date_day
group by dates.month_start, awards.main_procurement_category
order by dates.month_start, category
