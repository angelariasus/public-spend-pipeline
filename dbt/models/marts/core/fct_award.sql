{{ config(indexes=[
    {'columns': ['award_key'], 'unique': true},
    {'columns': ['ocid']},
    {'columns': ['entity_id']},
    {'columns': ['supplier_id']}
]) }}

-- One row per award. Each award in this source has a single supplier
-- (consortia are registered as one supplier).

with awards as (
    select * from {{ ref('int_oece__awards_pen') }}
),

award_suppliers as (
    select * from {{ ref('stg_oece__award_suppliers') }}
),

processes as (
    select * from {{ ref('stg_oece__records') }}
)

select
    -- Single-column key for BI tools; award_id is only unique within a process.
    {{ dbt_utils.generate_surrogate_key(['awards.ocid', 'awards.award_id']) }} as award_key,
    awards.ocid,
    awards.award_id,
    processes.buyer_id as entity_id,
    award_suppliers.supplier_id,
    awards.awarded_on,
    awards.source_period,
    processes.main_procurement_category,
    awards.award_currency,
    awards.award_amount,
    awards.exchange_rate_to_pen,
    awards.exchange_rate_source,
    awards.award_amount_pen
from awards
inner join processes
    on awards.ocid = processes.ocid
left join award_suppliers
    on
        awards.ocid = award_suppliers.ocid
        and awards.award_id = award_suppliers.award_id
