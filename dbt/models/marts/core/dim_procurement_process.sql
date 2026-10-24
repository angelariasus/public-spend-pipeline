{{ config(indexes=[{'columns': ['ocid'], 'unique': true}, {'columns': ['entity_id']}]) }}

-- One row per contracting process (tender), with its buying entity and the
-- number of investment projects it funds.

with records as (
    select * from {{ ref('stg_oece__records') }}
),

project_counts as (
    select
        ocid,
        max(project_count) as project_count
    from {{ ref('int_oece__process_projects') }}
    group by ocid
)

select
    records.ocid,
    records.tender_id,
    records.buyer_id as entity_id,
    records.source_period,
    records.tender_title,
    records.main_procurement_category,
    records.procurement_method,
    records.procurement_method_details,
    records.tender_published_at,
    {{ to_lima_date('records.tender_published_at') }} as tender_published_on,
    records.number_of_tenderers,
    records.tender_currency,
    records.tender_amount,
    records.tender_amount_pen,
    records.budget_project_ids,
    coalesce(project_counts.project_count, 0) as project_count,
    project_counts.ocid is not null as is_investment_linked
from records
left join project_counts
    on records.ocid = project_counts.ocid
