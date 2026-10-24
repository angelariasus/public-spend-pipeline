{{ config(indexes=[{'columns': ['ocid', 'item_id']}]) }}

with source as (
    select * from {{ source('oece', 'oece_com_ten_ite_additionalclassific') }}
)

select
    data ->> 'ocid' as ocid,
    {{ ocds('tender/items/0/id') }} as item_id,
    {{ ocds('tender/items/0/additionalClassifications/0/id') }} as classification_id,
    {{ ocds('tender/id') }} as tender_id,
    period as source_period,
    {{ ocds('tender/items/0/additionalClassifications/0/scheme') }} as classification_scheme,
    {{ ocds('tender/items/0/additionalClassifications/0/description') }}
        as classification_description,
    _loaded_at
from source
