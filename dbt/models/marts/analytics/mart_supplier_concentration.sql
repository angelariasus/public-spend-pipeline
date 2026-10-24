{{ config(indexes=[{'columns': ['entity_id', 'award_year'], 'unique': true}]) }}

-- How concentrated each entity's awarded amount is among its suppliers, per
-- year, measured with supplier shares and the Herfindahl-Hirschman Index.

with awards as (
    select
        entity_id,
        extract(year from awarded_on)::int as award_year,
        supplier_id,
        award_amount_pen
    from {{ ref('fct_award') }}
    where
        supplier_id is not null
        and awarded_on is not null
        and award_amount_pen > 0
),

supplier_totals as (
    select
        entity_id,
        award_year,
        supplier_id,
        count(*) as award_count,
        sum(award_amount_pen) as awarded_amount_pen
    from awards
    group by entity_id, award_year, supplier_id
),

shares as (
    select
        *,
        awarded_amount_pen
        / sum(awarded_amount_pen) over (partition by entity_id, award_year) as supplier_share,
        row_number() over (
            partition by entity_id, award_year
            order by awarded_amount_pen desc, supplier_id asc
        ) as supplier_rank
    from supplier_totals
),

concentration as (
    select
        entity_id,
        award_year,
        count(*) as supplier_count,
        sum(award_count) as award_count,
        sum(awarded_amount_pen) as awarded_amount_pen,
        max(supplier_id) filter (where supplier_rank = 1) as top_supplier_id,
        max(supplier_share) as top_supplier_share,
        sum(supplier_share) filter (where supplier_rank <= 5) as top_5_supplier_share,
        10000 * sum(supplier_share * supplier_share) as hhi
    from shares
    group by entity_id, award_year
)

select
    concentration.entity_id,
    entities.entity_name,
    entities.department,
    concentration.award_year,
    concentration.supplier_count,
    concentration.award_count,
    concentration.awarded_amount_pen,
    concentration.top_supplier_id,
    suppliers.supplier_name as top_supplier_name,
    concentration.top_supplier_share,
    concentration.top_5_supplier_share,
    concentration.hhi,
    -- Conventional antitrust thresholds for the HHI.
    case
        when concentration.hhi < 1500 then 'low'
        when concentration.hhi < 2500 then 'moderate'
        else 'high'
    end as concentration_level
from concentration
left join {{ ref('dim_entity') }} as entities
    on concentration.entity_id = entities.entity_id
left join {{ ref('dim_supplier') }} as suppliers
    on concentration.top_supplier_id = suppliers.supplier_id
