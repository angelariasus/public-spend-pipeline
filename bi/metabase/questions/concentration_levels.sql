select
    award_year::text as award_year,
    concentration_level,
    count(*) as entities
from marts.mart_supplier_concentration
group by award_year, concentration_level
order by award_year, concentration_level
