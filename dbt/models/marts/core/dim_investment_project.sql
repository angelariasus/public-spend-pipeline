{{ config(indexes=[{'columns': ['project_code'], 'unique': true}]) }}

-- Public investment projects (active and closed) from the MEF Banco de
-- Inversiones. Amounts are in soles.

select
    project_code,
    snip_code,
    project_name,
    status,
    is_closed,
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
    accrued_to_cost_pct,
    modified_budget_current_year,
    accrued_current_year,
    physical_progress_pct,
    registered_on,
    viability_on,
    physical_execution_start_on,
    physical_execution_end_on,
    first_accrual_month,
    last_accrual_month,
    closed_at
from {{ ref('int_mef__investments_unioned') }}
