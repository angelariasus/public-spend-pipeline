{{ config(indexes=[{'columns': ['supplier_id'], 'unique': true}]) }}

-- Companies, individuals and consortia that won at least one award.

with award_suppliers as (
    select * from {{ ref('stg_oece__award_suppliers') }}
),

awards as (
    select * from {{ ref('stg_oece__awards') }}
),

parties as (
    select * from {{ ref('stg_oece__parties') }}
),

latest as (
    select distinct on (award_suppliers.supplier_id)
        award_suppliers.supplier_id,
        award_suppliers.supplier_name,
        parties.legal_name,
        parties.address_department,
        parties.address_country
    from award_suppliers
    left join awards
        on
            award_suppliers.ocid = awards.ocid
            and award_suppliers.award_id = awards.award_id
    left join parties
        on
            award_suppliers.ocid = parties.ocid
            and award_suppliers.supplier_id = parties.party_id
    order by award_suppliers.supplier_id asc, awards.awarded_at desc nulls last
),

classified as (
    select
        *,
        substr(supplier_id, length('PE-RUC-') + 1) as tax_id
    from latest
)

select
    supplier_id,
    tax_id,
    coalesce(legal_name, supplier_name) as supplier_name,
    -- Peruvian RUC prefixes: 20 = company, 10/15/16/17 = individual. SEACE
    -- registers consortia with 6-7 digit codes and foreign suppliers with an
    -- L prefix.
    case
        when tax_id ~ '^20\d{9}$' then 'company'
        when tax_id ~ '^1[0567]\d{9}$' then 'individual'
        when tax_id ~ '^\d{6,7}$' then 'consortium'
        when tax_id ~ '^L\d+$' then 'foreign'
        else 'other'
    end as supplier_type,
    address_department as department,
    address_country as country
from classified
