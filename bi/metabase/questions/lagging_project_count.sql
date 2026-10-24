select count(*) as lagging_projects
from marts.mart_investment_vs_procurement
where is_lagging
