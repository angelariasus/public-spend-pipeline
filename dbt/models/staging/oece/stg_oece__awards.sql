{{ config(indexes=[{'columns': ['ocid']}, {'columns': ['award_id']}]) }}

with source as (
    select * from {{ source('oece', 'oece_com_awards') }}
)

select
    data ->> 'ocid' as ocid,
    {{ ocds('awards/0/id') }} as award_id,
    period as source_period,
    {{ to_timestamptz(ocds('awards/0/date')) }} as awarded_at,
    {{ to_numeric(ocds('awards/0/value/amount')) }} as award_amount,
    {{ ocds('awards/0/value/currency') }} as award_currency,
    _loaded_at
from source
