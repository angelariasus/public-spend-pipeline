{{ config(indexes=[{'columns': ['project_code'], 'unique': true}]) }}

-- One row per investment project funded by at least one contracting process in
-- the loaded periods: what was awarded and contracted through SEACE next to
-- what MEF reports as cost, spend and physical progress.

with process_projects as (
    select * from {{ ref('int_oece__process_projects') }}
),

processes as (
    select * from {{ ref('dim_procurement_process') }}
),

projects as (
    select * from {{ ref('dim_investment_project') }}
),

award_totals as (
    select
        ocid,
        count(*) as award_count,
        sum(award_amount_pen) as awarded_amount_pen
    from {{ ref('fct_award') }}
    group by ocid
),

contract_totals as (
    select
        ocid,
        count(*) as contract_count,
        sum(contract_amount_pen) as contracted_amount_pen,
        min(signed_on) as first_signed_on,
        max(signed_on) as last_signed_on
    from {{ ref('fct_contract') }}
    group by ocid
),

by_project as (
    select
        process_projects.project_code,
        count(*) as process_count,
        count(contract_totals.ocid) as contracted_process_count,
        count(*) filter (where process_projects.project_count > 1) as shared_process_count,
        coalesce(sum(award_totals.award_count), 0)::bigint as award_count,
        coalesce(sum(contract_totals.contract_count), 0)::bigint as contract_count,
        sum(processes.tender_amount_pen * process_projects.allocation_weight)
            as tendered_amount_pen,
        coalesce(sum(award_totals.awarded_amount_pen * process_projects.allocation_weight), 0)
            as awarded_amount_pen,
        coalesce(sum(contract_totals.contracted_amount_pen * process_projects.allocation_weight), 0)
            as contracted_amount_pen,
        min(processes.tender_published_on) as first_tender_published_on,
        max(processes.tender_published_on) as last_tender_published_on,
        min(contract_totals.first_signed_on) as first_contract_signed_on,
        max(contract_totals.last_signed_on) as last_contract_signed_on
    from process_projects
    inner join processes
        on process_projects.ocid = processes.ocid
    left join award_totals
        on process_projects.ocid = award_totals.ocid
    left join contract_totals
        on process_projects.ocid = contract_totals.ocid
    group by process_projects.project_code
)

select
    by_project.project_code,
    projects.project_code is not null as is_matched_in_mef,
    projects.project_name,
    projects.status,
    projects.is_closed,
    projects.government_level,
    projects.sector,
    projects.entity_name,
    projects.budget_function,
    projects.department,
    projects.province,
    projects.district,
    by_project.process_count,
    by_project.contracted_process_count,
    by_project.shared_process_count,
    by_project.award_count,
    by_project.contract_count,
    by_project.tendered_amount_pen,
    by_project.awarded_amount_pen,
    by_project.contracted_amount_pen,
    projects.viable_amount,
    projects.updated_cost,
    projects.accrued_total,
    projects.accrued_to_cost_pct,
    projects.physical_progress_pct,
    100 * by_project.contracted_amount_pen / nullif(projects.updated_cost, 0)
        as contracted_to_cost_pct,
    100 * projects.accrued_total / nullif(by_project.contracted_amount_pen, 0)
        as accrued_to_contracted_pct,
    by_project.first_tender_published_on,
    by_project.last_tender_published_on,
    by_project.first_contract_signed_on,
    by_project.last_contract_signed_on,
    -- Contracts far above the project cost usually mean the entity tagged
    -- processes with the wrong project code (or never updated the cost).
    coalesce(by_project.contracted_amount_pen > 1.5 * projects.updated_cost, false)
        as is_contracted_above_cost,
    -- Projects that signed at least S/ 1M in contracts over a year ago and
    -- still report less than 25% physical progress.
    coalesce(
        not projects.is_closed
        and by_project.contracted_amount_pen >= 1000000
        and by_project.first_contract_signed_on < current_date - interval '12 months'
        and projects.physical_progress_pct < 25,
        false
    ) as is_lagging
from by_project
left join projects
    on by_project.project_code = projects.project_code
