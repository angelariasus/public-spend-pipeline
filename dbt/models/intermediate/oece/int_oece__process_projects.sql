-- Bridge between contracting processes and the investment projects they fund.
-- budget_project_ids holds one MEF project code or a comma-separated list.

with records as (
    select
        ocid,
        budget_project_ids
    from {{ ref('stg_oece__records') }}
    where budget_project_ids is not null
),

exploded as (
    select distinct
        records.ocid,
        btrim(ids.project_code) as project_code
    from records
    cross join
        lateral unnest(string_to_array(records.budget_project_ids, ',')) as ids (project_code)
    where btrim(ids.project_code) != ''
)

select
    ocid,
    project_code,
    count(*) over (partition by ocid) as project_count,
    -- OCDS does not say how a multi-project process splits its amount, so it is
    -- shared equally. 99% of linked processes fund a single project.
    1.0 / count(*) over (partition by ocid) as allocation_weight
from exploded
