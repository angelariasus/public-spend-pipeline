{{ config(indexes=[{'columns': ['ocid', 'award_id']}]) }}

with source as (
    select * from {{ source('oece', 'oece_com_awa_val_exchangerates') }}
)

select
    data ->> 'ocid' as ocid,
    {{ ocds('awards/0/id') }} as award_id,
    period as source_period,
    -- Target currency of the conversion; the rate is units of it per unit of
    -- the award currency.
    {{ ocds('awards/0/value/exchangeRates/0/currency') }} as target_currency,
    {{ to_numeric(ocds('awards/0/value/exchangeRates/0/rate')) }} as exchange_rate,
    _loaded_at
from source
