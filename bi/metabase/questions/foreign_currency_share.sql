select
    sum(award_amount_pen) filter (where award_currency != 'PEN')
    / sum(award_amount_pen) as foreign_currency_share
from marts.fct_award
