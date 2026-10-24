-- Awards with their amount in soles. Most foreign-currency awards report their
-- own rate; the rest use that month's average rate for the currency.

with awards as (
    select * from {{ ref('stg_oece__awards') }}
),

award_rates as (
    select * from {{ ref('stg_oece__award_exchange_rates') }}
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
        awards.ocid,
        awards.award_id,
        awards.source_period,
        awards.awarded_at,
        {{ to_lima_date('awards.awarded_at') }} as awarded_on,
        awards.award_amount,
        awards.award_currency,
        case
            when awards.award_currency = 'PEN' then 1
            else
                coalesce(
                    award_rates.exchange_rate,
                    monthly_rates.exchange_rate,
                    currency_rates.currency_average_rate
                )
        end as exchange_rate_to_pen,
        case
            when awards.award_currency = 'PEN' then 'native'
            when award_rates.exchange_rate is not null then 'reported'
            when monthly_rates.exchange_rate is not null then 'monthly_average'
            when currency_rates.currency_average_rate is not null then 'currency_average'
        end as exchange_rate_source
    from awards
    left join award_rates
        on
            awards.ocid = award_rates.ocid
            and awards.award_id = award_rates.award_id
    left join monthly_rates
        on
            awards.award_currency = monthly_rates.currency
            and date_trunc('month', {{ to_lima_date('awards.awarded_at') }})
            = monthly_rates.rate_month
    left join currency_rates
        on awards.award_currency = currency_rates.currency
)

select
    *,
    award_amount * exchange_rate_to_pen as award_amount_pen
from converted
