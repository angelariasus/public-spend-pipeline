-- Department of the buying entity's address.
select
    coalesce(entities.department, 'UNKNOWN') as department,
    sum(awards.award_amount_pen) / 1e6 as awarded_millions_pen
from marts.fct_award as awards
inner join marts.dim_entity as entities
    on awards.entity_id = entities.entity_id
group by entities.department
order by awarded_millions_pen desc
