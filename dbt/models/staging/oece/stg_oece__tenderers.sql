{{ config(indexes=[{'columns': ['ocid']}, {'columns': ['tenderer_id']}]) }}

with source as (
    select * from {{ source('oece', 'oece_com_ten_tenderers') }}
)

select
    data ->> 'ocid' as ocid,
    {{ ocds('tender/tenderers/0/id') }} as tenderer_id,
    {{ ocds('tender/id') }} as tender_id,
    period as source_period,
    {{ ocds('tender/tenderers/0/name') }} as tenderer_name,
    _loaded_at
from source
