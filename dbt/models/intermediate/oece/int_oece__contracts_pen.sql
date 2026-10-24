-- Contracts with their amounts in soles. Half of the foreign-currency contracts
-- come without a rate; they fall back to their award's rate, then to the
-- month's average rate for the currency.

with contracts as (
    select * from {{ ref('stg_oece__contracts') }}
),

contract_rates as (
    select * from {{ ref('stg_oece__contract_exchange_rates') }}
),

awards as (
    select * from {{ ref('int_oece__awards_pen') }}
),

monthly_rates as (
    select * from {{ ref('int_oece__exchange_rates_monthly') }}
),

currency_rates as (
    select distinct
        currency,
        currency_average_rate
    from monthly_rates
),

converted as (
    select
        contracts.ocid,
        contracts.contract_id,
        contracts.award_id,
        contracts.source_period,
        contracts.contract_title,
        contracts.signed_at,
        {{ to_lima_date('contracts.signed_at') }} as signed_on,
        {{ to_lima_date('contracts.period_start_at') }} as period_start_on,
        {{ to_lima_date('contracts.period_end_at') }} as period_end_on,
        contracts.duration_days,
        contracts.contract_amount,
        contracts.final_amount,
        contracts.contract_currency,
        awards.award_id is not null as has_award,
        case
            when contracts.contract_currency = 'PEN' then 1
            else
                coalesce(
                    contract_rates.exchange_rate,
                    case
                        when awards.award_currency = contracts.contract_currency
                            and awards.exchange_rate_source = 'reported'
                            then awards.exchange_rate_to_pen
                    end,
                    monthly_rates.exchange_rate,
                    currency_rates.currency_average_rate
                )
        end as exchange_rate_to_pen,
        case
            when contracts.contract_currency = 'PEN' then 'native'
            when contract_rates.exchange_rate is not null then 'reported'
            when awards.award_currency = contracts.contract_currency
                and awards.exchange_rate_source = 'reported'
                then 'award'
            when monthly_rates.exchange_rate is not null then 'monthly_average'
            when currency_rates.currency_average_rate is not null then 'currency_average'
        end as exchange_rate_source
    from contracts
    left join contract_rates
        on
            contracts.ocid = contract_rates.ocid
            and contracts.contract_id = contract_rates.contract_id
    left join awards
        on
            contracts.ocid = awards.ocid
            and contracts.award_id = awards.award_id
    left join monthly_rates
        on
            contracts.contract_currency = monthly_rates.currency
            and date_trunc('month', {{ to_lima_date('contracts.signed_at') }})
            = monthly_rates.rate_month
    left join currency_rates
        on contracts.contract_currency = currency_rates.currency
)

select
    *,
    contract_amount * exchange_rate_to_pen as contract_amount_pen,
    -- The final value is always reported in the contract currency.
    final_amount * exchange_rate_to_pen as final_amount_pen
from converted
