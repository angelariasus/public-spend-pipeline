select
    suppliers.supplier_type,
    sum(awards.award_amount_pen) as awarded_amount_pen
from marts.fct_award as awards
inner join marts.dim_supplier as suppliers
    on awards.supplier_id = suppliers.supplier_id
group by suppliers.supplier_type
order by awarded_amount_pen desc
