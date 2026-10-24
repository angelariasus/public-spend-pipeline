select coalesce(sum(contracted_amount_pen), 0) as contracted_amount_pen
from marts.mart_investment_vs_procurement
where is_lagging
