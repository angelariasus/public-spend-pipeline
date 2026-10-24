select
    project_code,
    project_name,
    entity_name,
    department,
    contracted_amount_pen,
    updated_cost,
    accrued_total,
    physical_progress_pct,
    first_contract_signed_on
from marts.mart_investment_vs_procurement
where is_lagging
order by contracted_amount_pen desc
limit 100
