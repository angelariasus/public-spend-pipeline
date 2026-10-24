{{ config(indexes=[{'columns': ['ocid']}, {'columns': ['party_id']}]) }}

with source as (
    select * from {{ source('oece', 'oece_com_parties') }}
),

renamed as (
    select
        data ->> 'ocid' as ocid,
        {{ ocds('parties/0/id') }} as party_id,
        period as source_period,
        {{ ocds('parties/0/name') }} as party_name,
        {{ ocds('parties/0/identifier/legalName') }} as legal_name,
        {{ ocds('parties/0/identifier/scheme') }} as identifier_scheme,
        {{ ocds('parties/0/identifier/id') }} as identifier_id,
        string_to_array({{ ocds('parties/0/roles') }}, ';') as party_roles,
        {{ ocds('parties/0/address/department') }} as address_department,
        {{ ocds('parties/0/address/region') }} as address_region,
        {{ ocds('parties/0/address/locality') }} as address_locality,
        {{ ocds('parties/0/address/countryName') }} as address_country,
        _loaded_at
    from source
)

select
    *,
    'buyer' = any(party_roles) as is_buyer,
    'tenderer' = any(party_roles) as is_tenderer,
    'supplier' = any(party_roles) as is_supplier
from renamed
