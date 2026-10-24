{{ config(indexes=[{'columns': ['ocid']}]) }}

with source as (
    select * from {{ source('oece', 'oece_com_ten_items') }}
)

select
    data ->> 'ocid' as ocid,
    {{ ocds('tender/items/0/id') }} as item_id,
    {{ ocds('tender/id') }} as tender_id,
    period as source_period,
    {{ to_integer(ocds('tender/items/0/position')) }} as item_position,
    {{ ocds('tender/items/0/description') }} as item_description,
    {{ ocds('tender/items/0/status') }} as item_status,
    {{ ocds('tender/items/0/statusDetails') }} as item_status_details,
    {{ to_numeric(ocds('tender/items/0/quantity')) }} as quantity,
    {{ ocds('tender/items/0/unit/name') }} as unit_name,
    {{ to_numeric(ocds('tender/items/0/totalValue/amount')) }} as total_amount,
    {{ ocds('tender/items/0/totalValue/currency') }} as total_currency,
    {{ ocds('tender/items/0/classification/scheme') }} as classification_scheme,
    {{ ocds('tender/items/0/classification/id') }} as classification_id,
    {{ ocds('tender/items/0/classification/description') }} as classification_description,
    _loaded_at
from source
