{{ config(indexes=[
    {'columns': ['contract_key'], 'unique': true},
    {'columns': ['ocid']},
    {'columns': ['entity_id']},
    {'columns': ['supplier_id']}
]) }}

-- One row per signed contract, with its supplier taken from the award.

with contracts as (
    select * from {{ ref('int_oece__contracts_pen') }}
),

awards as (
    select * from {{ ref('fct_award') }}
),

processes as (
    select * from {{ ref('stg_oece__records') }}
)

select
    {{ dbt_utils.generate_surrogate_key(['contracts.ocid', 'contracts.contract_id']) }}
        as contract_key,
    contracts.ocid,
    contracts.contract_id,
    -- NULL when the award is missing from the source (~1k contracts).
    awards.award_key,
    processes.buyer_id as entity_id,
    awards.supplier_id,
    contracts.signed_on,
    contracts.period_start_on,
    contracts.period_end_on,
    contracts.duration_days,
    contracts.source_period,
    processes.main_procurement_category,
    contracts.contract_title,
    contracts.contract_currency,
    contracts.contract_amount,
    contracts.final_amount,
    contracts.exchange_rate_to_pen,
    contracts.exchange_rate_source,
    contracts.contract_amount_pen,
    contracts.final_amount_pen
from contracts
inner join processes
    on contracts.ocid = processes.ocid
left join awards
    on
        contracts.ocid = awards.ocid
        and contracts.award_id = awards.award_id
