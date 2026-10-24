{{ config(indexes=[{'columns': ['entity_id'], 'unique': true}]) }}

-- Public entities that buy through SEACE, identified by their OECE code.
-- Names and addresses change over time; the latest process wins.

with records as (
    select * from {{ ref('stg_oece__records') }}
),

parties as (
    select * from {{ ref('stg_oece__parties') }}
),

latest_party as (
    select distinct on (records.buyer_id)
        records.buyer_id,
        records.buyer_name,
        parties.legal_name,
        parties.address_department,
        parties.address_region,
        parties.address_locality
    from records
    left join parties
        on
            records.ocid = parties.ocid
            and records.buyer_id = parties.party_id
    order by records.buyer_id asc, records.tender_published_at desc nulls last, records.ocid desc
),

activity as (
    select
        buyer_id,
        count(*) as process_count,
        min(tender_published_at) as first_tender_published_at,
        max(tender_published_at) as last_tender_published_at
    from records
    group by buyer_id
)

select
    latest_party.buyer_id as entity_id,
    coalesce(latest_party.legal_name, latest_party.buyer_name) as entity_name,
    latest_party.address_department as department,
    latest_party.address_region as province,
    latest_party.address_locality as district,
    activity.process_count,
    activity.first_tender_published_at,
    activity.last_tender_published_at
from latest_party
inner join activity
    on latest_party.buyer_id = activity.buyer_id
