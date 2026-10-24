-- Active and closed investments with the columns both files share. Finished
-- projects move from the active file to the closed one, so a process can only
-- be matched to its project by looking at both.

with active as (
    select * from {{ ref('stg_mef__investments') }}
),

closed as (
    select * from {{ ref('stg_mef__closed_investments') }}
),

unioned as (
    select
        project_code,
        snip_code,
        project_name,
        status,
        false as is_closed,
        government_level,
        sector,
        entity_name,
        executing_unit_code,
        executing_unit_name,
        investment_type,
        typology,
        budget_function,
        department,
        province,
        district,
        ubigeo,
        latitude,
        longitude,
        beneficiaries,
        viable_amount,
        updated_cost,
        -- Accrued spend is split by year in the active file.
        coalesce(accrued_until_last_year, 0) + coalesce(accrued_current_year, 0) as accrued_total,
        modified_budget_current_year,
        accrued_current_year,
        physical_progress_pct,
        registered_on,
        viability_on,
        physical_execution_start_on,
        physical_execution_end_on,
        first_accrual_month,
        last_accrual_month,
        null::timestamp as closed_at,
        _loaded_at
    from active

    union all

    select
        project_code,
        snip_code,
        project_name,
        status,
        true as is_closed,
        government_level,
        sector,
        entity_name,
        executing_unit_code,
        executing_unit_name,
        investment_type,
        typology,
        budget_function,
        department,
        province,
        district,
        ubigeo,
        latitude,
        longitude,
        beneficiaries,
        viable_amount,
        updated_cost,
        accrued_total,
        null::numeric as modified_budget_current_year,
        null::numeric as accrued_current_year,
        -- The closed file has no physical progress column.
        null::numeric as physical_progress_pct,
        registered_on,
        viability_on,
        physical_execution_start_on,
        physical_execution_end_on,
        first_accrual_month,
        last_accrual_month,
        closed_at,
        _loaded_at
    from closed
)

select
    *,
    100 * accrued_total / nullif(updated_cost, 0) as accrued_to_cost_pct
from unioned
where project_code is not null
