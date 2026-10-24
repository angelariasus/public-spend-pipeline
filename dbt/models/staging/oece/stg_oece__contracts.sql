{{ config(indexes=[{'columns': ['ocid']}, {'columns': ['award_id']}]) }}

with source as (
    select * from {{ source('oece', 'oece_com_contracts') }}
)

select
    data ->> 'ocid' as ocid,
    {{ ocds('contracts/0/id') }} as contract_id,
    {{ ocds('contracts/0/awardID') }} as award_id,
    period as source_period,
    {{ ocds('contracts/0/title') }} as contract_title,
    {{ ocds('contracts/0/description') }} as contract_description,
    {{ to_timestamptz(ocds('contracts/0/dateSigned')) }} as signed_at,
    {{ to_timestamptz(ocds('contracts/0/period/startDate')) }} as period_start_at,
    {{ to_timestamptz(ocds('contracts/0/period/endDate')) }} as period_end_at,
    {{ to_integer(ocds('contracts/0/period/durationInDays')) }} as duration_days,
    {{ to_numeric(ocds('contracts/0/value/amount')) }} as contract_amount,
    {{ ocds('contracts/0/value/currency') }} as contract_currency,
    {{ to_numeric(ocds('contracts/0/implementation/finalValue/amount')) }} as final_amount,
    {{ ocds('contracts/0/implementation/finalValue/currency') }} as final_currency,
    {{ to_timestamptz(ocds('contracts/0/implementation/endDate')) }} as implementation_end_at,
    _loaded_at
from source
