"""Stand-ins for the dbt_utils macros used by the models.

sqlfluff's jinja templater exposes each module in ``library_path`` as a jinja
variable, so ``dbt_utils.date_spine(...)`` renders to representative SQL that
can be parsed and linted without compiling the dbt project.
"""


def date_spine(datepart, start_date, end_date):
    step = f"interval '1 {datepart}'"
    return f"select generate_series({start_date}, {end_date}, {step}) as date_{datepart}"


def generate_surrogate_key(field_list):
    return "md5(" + " || '-' || ".join(f"coalesce({field}::text, '')" for field in field_list) + ")"
