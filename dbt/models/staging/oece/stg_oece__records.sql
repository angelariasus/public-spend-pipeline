{{ config(indexes=[{'columns': ['ocid'], 'unique': true}, {'columns': ['buyer_id']}]) }}

with source as (
    select * from {{ source('oece', 'oece_records') }}
),

renamed as (
    select
        data ->> 'ocid' as ocid,
        {{ ocds('tender/id') }} as tender_id,
        period as source_period,
        {{ ocds('buyer/id') }} as buyer_id,
        {{ ocds('buyer/name') }} as buyer_name,
        {{ ocds('tender/procuringEntity/id') }} as procuring_entity_id,
        {{ ocds('tender/procuringEntity/name') }} as procuring_entity_name,
        {{ ocds('tender/title') }} as tender_title,
        {{ ocds('tender/description') }} as tender_description,
        {{ ocds('tender/mainProcurementCategory') }} as main_procurement_category,
        {{ ocds('tender/procurementMethod') }} as procurement_method,
        {{ ocds('tender/procurementMethodDetails') }} as procurement_method_details,
        {{ to_timestamptz(ocds('tender/datePublished')) }} as tender_published_at,
        {{ to_timestamptz(ocds('tender/tenderPeriod/startDate')) }} as tender_period_start_at,
        {{ to_timestamptz(ocds('tender/tenderPeriod/endDate')) }} as tender_period_end_at,
        {{ to_integer(ocds('tender/numberOfTenderers')) }} as number_of_tenderers,
        {{ to_boolean(ocds('tender/hasTenderInformationProtectedByLaw')) }}
            as has_protected_tender_information,
        {{ to_numeric(ocds('tender/value/amount')) }} as tender_amount,
        {{ ocds('tender/value/currency') }} as tender_currency,
        {{ to_numeric(ocds('tender/value/amount_PEN')) }} as tender_amount_pen_reported,
        {{ ocds('planning/budget/projectID') }} as budget_project_ids,
        {{ ocds('planning/budget/project') }} as budget_project_name,
        {{ ocds('planning/budget/description') }} as budget_description,
        {{ to_numeric(ocds('planning/budget/amount/amount')) }} as budget_amount,
        {{ ocds('planning/budget/amount/currency') }} as budget_currency,
        {{ to_timestamptz(ocds('date')) }} as record_updated_at,
        _loaded_at
    from source
)

select
    *,
    -- The portal reports amount_PEN = 0 for ~5k tenders that are already in
    -- soles, so the original amount is used whenever the currency is PEN.
    case
        when tender_currency = 'PEN' then tender_amount
        else nullif(tender_amount_pen_reported, 0)
    end as tender_amount_pen
from renamed
