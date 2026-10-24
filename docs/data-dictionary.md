# Data dictionary

Columns of the `marts` schema, the layer read by Metabase and Power BI.
Generated from the dbt manifest and catalog with
`python -m public_spend.docs.data_dictionary`; edit the descriptions in
`dbt/models/marts/**/*.yml` instead of this file. Key columns are in bold.

## Dimensions and facts

### dim_date

`marts.dim_date`. Calendar from 2000 to 2030, one row per day.

| Column | Type | Description |
|--------|------|-------------|
| **date_day** | date | Calendar date; the key. |
| calendar_year | integer | Four-digit year. |
| calendar_quarter | integer | Quarter of the year, 1 to 4. |
| calendar_month | integer | Month of the year, 1 to 12. |
| calendar_year_month | text | Year and month as `YYYY-MM`, for sorting and labels. |
| month_start | date | First day of the month; the join key for monthly aggregates. |
| month_name | text | English month name. |
| iso_day_of_week | integer | ISO weekday, 1 (Monday) to 7 (Sunday). |
| is_weekend | boolean | True on Saturdays and Sundays. |

### dim_entity

`marts.dim_entity`. Public entities that buy through SEACE, one row per entity. The name and address come from the entity's most recently published process.

| Column | Type | Description |
|--------|------|-------------|
| **entity_id** | text | OECE entity code (`PE-CONSUCODE-...`), the buyer of a process. |
| entity_name | text | Legal name from the parties table, or the buyer name when missing. |
| department | text | Department (region) of the entity's address. |
| province | text | Province of the entity's address. |
| district | text | District of the entity's address. |
| process_count | bigint | Contracting processes published by the entity in the loaded periods. |
| first_tender_published_at | timestamp with time zone | Publication timestamp of the entity's earliest loaded process. |
| last_tender_published_at | timestamp with time zone | Publication timestamp of the entity's latest loaded process. |

### dim_investment_project

`marts.dim_investment_project`. Public investment projects from the MEF Banco de Inversiones, active and closed, one row per project. Amounts are in soles. Columns that only the active file reports are NULL for closed projects.

| Column | Type | Description |
|--------|------|-------------|
| **project_code** | text | MEF `CODIGO_UNICO`; the key, shared with OCDS budget project IDs. |
| snip_code | text | Legacy SNIP code, for projects registered before Invierte.pe. |
| project_name | text | Project name as registered in MEF. |
| status | text | ACTIVO (active file) or CERRADO (closed file). |
| is_closed | boolean | True for projects from the closed-investments file. |
| government_level | text | GN (national), GR (regional) or GL (local government). |
| sector | text | Government sector responsible for the project. |
| entity_name | text | Entity that owns the project in MEF. |
| executing_unit_code | text | Budget code of the executing unit. |
| executing_unit_name | text | Name of the executing unit. |
| investment_type | text | MEF investment type (project, IOARR, program, ...). |
| typology | text | MEF typology of the project. |
| budget_function | text | Budget function (transport, education, health, ...). |
| department | text | Department where the project is located. |
| province | text | Province where the project is located. |
| district | text | District where the project is located. |
| ubigeo | text | INEI geographic code of the district. |
| latitude | numeric | Latitude of the project, NULL when MEF reports 0. |
| longitude | numeric | Longitude of the project, NULL when MEF reports 0. |
| beneficiaries | bigint | Number of beneficiaries declared for the project. |
| viable_amount | numeric | Investment amount when the project was declared viable, in soles. |
| updated_cost | numeric | Current total cost of the project, in soles. |
| accrued_total | numeric | Spend accrued over the whole life of the project, in soles. |
| accrued_to_cost_pct | numeric | Accrued spend as a percentage of the updated cost. |
| modified_budget_current_year | numeric | Modified budget (PIM) for the current year, in soles. Active projects only. |
| accrued_current_year | numeric | Spend accrued in the current year, in soles. Active projects only. |
| physical_progress_pct | numeric | Physical progress reported by the entity, in percent. Active projects only. |
| registered_on | date | Date the project was registered in the Banco de Inversiones. |
| viability_on | date | Date the project was declared viable or approved. |
| physical_execution_start_on | date | Reported start of physical execution. |
| physical_execution_end_on | date | Reported or planned end of physical execution. |
| first_accrual_month | date | Month of the first accrued spend. |
| last_accrual_month | date | Month of the latest accrued spend. |
| closed_at | timestamp without time zone | When the project was closed. Closed projects only. |

### dim_procurement_process

`marts.dim_procurement_process`. One row per contracting process (tender) published by OECE in the loaded periods, with its buying entity and the investment projects it funds.

| Column | Type | Description |
|--------|------|-------------|
| **ocid** | text | Open Contracting ID of the process; the key. |
| tender_id | text | SEACE process nomenclature, e.g. `LP-SM-9-2024-INVERMET-1`. |
| entity_id | text | Buying entity; references `dim_entity`. |
| source_period | date | Month of the OECE bulk file the process was loaded from. |
| tender_title | text | Title of the tender. |
| main_procurement_category | text | OCDS category - goods, services or works. |
| procurement_method | text | OCDS method - open, selective, limited or direct. NULL for a third of processes. |
| procurement_method_details | text | SEACE procedure type (licitación pública, adjudicación simplificada, ...). |
| tender_published_at | timestamp with time zone | Publication timestamp of the tender. |
| tender_published_on | date | Publication date in Lima time; references `dim_date`. |
| number_of_tenderers | bigint | Bidders that took part in the tender. |
| tender_currency | text | Currency of the estimated tender value. |
| tender_amount | numeric | Estimated tender value in its original currency. |
| tender_amount_pen | numeric | Estimated tender value in soles, as reported by OECE. |
| budget_project_ids | text | Raw list of MEF project codes funded by the process, comma-separated. |
| project_count | bigint | Investment projects funded by the process (0 when none). |
| is_investment_linked | boolean | True when the process funds at least one investment project. |

### dim_supplier

`marts.dim_supplier`. Suppliers that won at least one award, one row per supplier ID.

| Column | Type | Description |
|--------|------|-------------|
| **supplier_id** | text | OCDS supplier ID (`PE-RUC-...`), as published by OECE. |
| tax_id | text | The ID without its `PE-RUC-` prefix; a RUC, a consortium code or a foreign ID. |
| supplier_name | text | Legal name from the parties table, or the name on the latest award. |
| supplier_type | text | Derived from the ID: company (RUC starting with 20), individual (RUC starting with 10, 15, 16 or 17), consortium (6-7 digit SEACE code), foreign (L prefix) or other. |
| department | text | Department of the supplier's address, when published. |
| country | text | Country of the supplier's address, when published. |

### fct_award

`marts.fct_award`. One row per award, with its amount in the original currency and in soles. Awards in this source have a single supplier; consortia are registered as one supplier.

| Column | Type | Description |
|--------|------|-------------|
| **award_key** | text | Surrogate key of (`ocid`, `award_id`), for single-column joins in BI tools. |
| ocid | text | Process the award belongs to; references `dim_procurement_process`. |
| award_id | text | Award ID as published; only unique within a process. |
| entity_id | text | Buying entity; references `dim_entity`. |
| supplier_id | text | Winning supplier; references `dim_supplier`. NULL for ~3k awards published without one. |
| awarded_on | date | Award date in Lima time; references `dim_date`. |
| source_period | date | Month of the OECE bulk file the award was loaded from. |
| main_procurement_category | text | Category of the process - goods, services or works. |
| award_currency | text | ISO code of the award currency. |
| award_amount | numeric | Awarded amount in its original currency. |
| exchange_rate_to_pen | numeric | Soles per unit of the award currency (1 for PEN). |
| exchange_rate_source | text | Where the rate came from: native (PEN), reported (by the award), monthly_average (of the currency in that month) or currency_average (over all months). |
| award_amount_pen | numeric | Awarded amount in soles. |

### fct_contract

`marts.fct_contract`. One row per signed contract, with its amounts in the original currency and in soles. The supplier is taken from the contract's award.

| Column | Type | Description |
|--------|------|-------------|
| **contract_key** | text | Surrogate key of (`ocid`, `contract_id`). |
| ocid | text | Process the contract belongs to; references `dim_procurement_process`. |
| contract_id | text | Contract ID as published; only unique within a process. |
| award_key | text | Award the contract implements; references `fct_award`. NULL when the award is missing from the source. |
| entity_id | text | Buying entity; references `dim_entity`. |
| supplier_id | text | Supplier of the award; references `dim_supplier`. |
| signed_on | date | Signature date in Lima time; references `dim_date`. |
| period_start_on | date | Start of the contract period. |
| period_end_on | date | End of the contract period. |
| duration_days | bigint | Contract duration in days, as published. |
| source_period | date | Month of the OECE bulk file the contract was loaded from. |
| main_procurement_category | text | Category of the process - goods, services or works. |
| contract_title | text | Contract number or title, as published. |
| contract_currency | text | ISO code of the contract currency. |
| contract_amount | numeric | Contract amount in its original currency. |
| final_amount | numeric | Final value after implementation, in the contract currency. Reported for ~10% of contracts. |
| exchange_rate_to_pen | numeric | Soles per unit of the contract currency (1 for PEN). |
| exchange_rate_source | text | Where the rate came from: native, reported (by the contract), award (reported by its award), monthly_average or currency_average. |
| contract_amount_pen | numeric | Contract amount in soles. |
| final_amount_pen | numeric | Final value in soles, when reported. |

## Analytical marts

### mart_investment_vs_procurement

`marts.mart_investment_vs_procurement`. One row per investment project funded by a contracting process in the loaded periods. Compares the amounts tendered, awarded and contracted through SEACE with MEF's updated cost, accrued spend and physical progress. Amounts of processes that fund several projects are split equally among them.

| Column | Type | Description |
|--------|------|-------------|
| **project_code** | text | MEF `CODIGO_UNICO`; the key. |
| is_matched_in_mef | boolean | False when the code is in neither MEF file (MEF columns are NULL). |
| project_name | text | Project name from MEF. |
| status | text | ACTIVO or CERRADO. |
| is_closed | boolean | True for projects from the closed-investments file. |
| government_level | text | GN (national), GR (regional) or GL (local government). |
| sector | text | Government sector responsible for the project. |
| entity_name | text | Entity that owns the project in MEF. |
| budget_function | text | Budget function of the project. |
| department | text | Department where the project is located. |
| province | text | Province where the project is located. |
| district | text | District where the project is located. |
| process_count | bigint | Contracting processes that list the project in their budget. |
| contracted_process_count | bigint | Those processes that have at least one signed contract. |
| shared_process_count | bigint | Processes that fund this project together with others. |
| award_count | bigint | Awards across the project's processes. |
| contract_count | bigint | Contracts across the project's processes. |
| tendered_amount_pen | numeric | Estimated tender value attributed to the project, in soles. |
| awarded_amount_pen | numeric | Awarded amount attributed to the project, in soles. |
| contracted_amount_pen | numeric | Contracted amount attributed to the project, in soles. |
| viable_amount | numeric | MEF investment amount at viability, in soles. |
| updated_cost | numeric | MEF current total cost, in soles. |
| accrued_total | numeric | MEF spend accrued over the whole life of the project, in soles. |
| accrued_to_cost_pct | numeric | Accrued spend as a percentage of the updated cost. |
| physical_progress_pct | numeric | Physical progress reported to MEF, in percent. Active projects only. |
| contracted_to_cost_pct | numeric | Contracted amount as a percentage of the project's updated cost. |
| accrued_to_contracted_pct | numeric | MEF accrued spend as a percentage of the contracted amount. Accrued spend covers the whole project life, including contracts signed before the loaded periods, so values above 100 are expected. |
| first_tender_published_on | date | Earliest tender publication date among the project's processes. |
| last_tender_published_on | date | Latest tender publication date among the project's processes. |
| first_contract_signed_on | date | Earliest contract signature date among the project's processes. |
| last_contract_signed_on | date | Latest contract signature date among the project's processes. |
| is_contracted_above_cost | boolean | Contracted amount above 150% of the updated cost. Usually a process tagged with the wrong project code (e.g. an entity reusing one small project's code for its large works) or a cost never updated in MEF. |
| is_lagging | boolean | Active project with at least S/ 1M contracted, a first contract signed more than 12 months ago and less than 25% physical progress. |

### mart_supplier_concentration

`marts.mart_supplier_concentration`. Supplier concentration of each entity's awards per year. Only awards with a supplier, a date and a positive amount are counted.

| Column | Type | Description |
|--------|------|-------------|
| entity_id | text | Buying entity; references `dim_entity`. |
| entity_name | text | Name of the entity. |
| department | text | Department of the entity's address. |
| award_year | integer | Calendar year of the award date, in Lima time. |
| supplier_count | bigint | Distinct suppliers awarded by the entity in the year. |
| award_count | bigint | Awards made by the entity in the year. |
| awarded_amount_pen | numeric | Total awarded by the entity in the year, in soles. |
| top_supplier_id | text | Supplier with the largest awarded amount; references `dim_supplier`. |
| top_supplier_name | text | Name of the top supplier. |
| top_supplier_share | numeric | Share of the awarded amount won by the largest supplier (0-1). |
| top_5_supplier_share | numeric | Share of the awarded amount won by the five largest suppliers (0-1). |
| hhi | numeric | Herfindahl-Hirschman Index of supplier shares, from near 0 (many small suppliers) to 10,000 (a single supplier). |
| concentration_level | text | low (HHI < 1,500), moderate (< 2,500) or high. |
