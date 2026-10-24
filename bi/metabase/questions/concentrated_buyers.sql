-- Entities that awarded at least S/ 10M in a year, most concentrated first.
select
    entity_name,
    award_year::text as award_year,
    awarded_amount_pen,
    supplier_count,
    top_supplier_name,
    top_supplier_share,
    hhi
from marts.mart_supplier_concentration
where awarded_amount_pen >= 10000000
order by hhi desc, awarded_amount_pen desc
limit 100
