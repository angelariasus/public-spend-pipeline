-- Active and closed investments must not share a project code, otherwise
-- unioning them downstream would double count.
select active.project_code
from {{ ref('stg_mef__investments') }} as active
inner join {{ ref('stg_mef__closed_investments') }} as closed
    on active.project_code = closed.project_code
