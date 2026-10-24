{{ config(indexes=[{'columns': ['ocid', 'contract_id']}]) }}

with source as (
    select * from {{ source('oece', 'oece_com_con_val_exchangerates') }}
)

select
    data ->> 'ocid' as ocid,
    {{ ocds('contracts/0/id') }} as contract_id,
    period as source_period,
    {{ ocds('contracts/0/value/exchangeRates/0/currency') }} as target_currency,
    {{ to_numeric(ocds('contracts/0/value/exchangeRates/0/rate')) }} as exchange_rate,
    _loaded_at
from source
