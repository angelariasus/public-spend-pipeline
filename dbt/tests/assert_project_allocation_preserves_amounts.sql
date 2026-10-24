-- Splitting multi-project processes among their projects must neither lose nor
-- duplicate money: the mart total equals the total of the linked processes.

with linked_processes as (
    select distinct ocid
    from {{ ref('int_oece__process_projects') }}
),

expected as (
    select coalesce(sum(contracts.contract_amount_pen), 0) as contracted_amount_pen
    from {{ ref('fct_contract') }} as contracts
    inner join linked_processes
        on contracts.ocid = linked_processes.ocid
),

actual as (
    select sum(contracted_amount_pen) as contracted_amount_pen
    from {{ ref('mart_investment_vs_procurement') }}
)

select
    expected.contracted_amount_pen as expected_amount,
    actual.contracted_amount_pen as actual_amount
from expected
cross join actual
where abs(expected.contracted_amount_pen - actual.contracted_amount_pen) > 1
