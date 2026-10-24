select
    entities.entity_name,
    sum(awards.award_amount_pen) / 1e6 as awarded_millions_pen
from marts.fct_award as awards
inner join marts.dim_entity as entities
    on awards.entity_id = entities.entity_id
group by entities.entity_name
order by awarded_millions_pen desc
limit 15
