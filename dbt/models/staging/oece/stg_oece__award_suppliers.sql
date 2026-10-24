{{ config(indexes=[{'columns': ['ocid', 'award_id']}, {'columns': ['supplier_id']}]) }}

with source as (
    select * from {{ source('oece', 'oece_com_awa_suppliers') }}
)

select
    data ->> 'ocid' as ocid,
    {{ ocds('awards/0/id') }} as award_id,
    {{ ocds('awards/0/suppliers/0/id') }} as supplier_id,
    period as source_period,
    {{ ocds('awards/0/suppliers/0/name') }} as supplier_name,
    _loaded_at
from source
