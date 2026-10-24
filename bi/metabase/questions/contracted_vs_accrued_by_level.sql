-- GN = national, GR = regional, GL = local government.
select
    government_level,
    sum(contracted_amount_pen) / 1e6 as contracted_millions_pen,
    sum(accrued_total) / 1e6 as accrued_millions_pen
from marts.mart_investment_vs_procurement
where is_matched_in_mef
group by government_level
order by contracted_millions_pen desc
