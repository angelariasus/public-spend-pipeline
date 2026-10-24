-- Average rate to soles per currency and month, from every award and contract
-- that reports one. Used to convert amounts that come without their own rate.

with awards as (
    select * from {{ ref('stg_oece__awards') }}
),

award_rates as (
    select * from {{ ref('stg_oece__award_exchange_rates') }}
),

contracts as (
    select * from {{ ref('stg_oece__contracts') }}
),

contract_rates as (
    select * from {{ ref('stg_oece__contract_exchange_rates') }}
),

observed_rates as (
    select
        awards.award_currency as currency,
        date_trunc('month', {{ to_lima_date('awards.awarded_at') }})::date as rate_month,
        award_rates.exchange_rate
    from award_rates
    inner join awards
        on
            award_rates.ocid = awards.ocid
            and award_rates.award_id = awards.award_id

    union all

    select
        contracts.contract_currency as currency,
        date_trunc('month', {{ to_lima_date('contracts.signed_at') }})::date as rate_month,
        contract_rates.exchange_rate
    from contract_rates
    inner join contracts
        on
            contract_rates.ocid = contracts.ocid
            and contract_rates.contract_id = contracts.contract_id
),

monthly as (
    select
        currency,
        rate_month,
        avg(exchange_rate) as exchange_rate,
        count(*) as observations
    from observed_rates
    where rate_month is not null
    group by currency, rate_month
)

select
    *,
    -- Last-resort rate for months in which a currency has no observation.
    sum(exchange_rate * observations) over (partition by currency)
    / sum(observations) over (partition by currency) as currency_average_rate
from monthly
