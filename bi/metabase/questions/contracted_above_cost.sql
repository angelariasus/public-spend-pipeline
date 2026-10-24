-- Usually processes tagged with the wrong project code, or costs never updated.
select
    project_code,
    project_name,
    entity_name,
    contracted_amount_pen,
    updated_cost,
    contracted_to_cost_pct,
    process_count
from marts.mart_investment_vs_procurement
where is_contracted_above_cost
order by contracted_amount_pen - updated_cost desc
limit 100
