{{ config(indexes=[{'columns': ['project_code']}]) }}

with source as (
    select
        *,
        row_number() over () as source_row
    from {{ source('mef', 'mef_investments') }}
),

deduplicated as (
    -- The snapshot repeats a few projects (e.g. 2022788) with one row whose
    -- technical file amount is 0. Keep the row with the highest amount; rows
    -- without a project code are all kept.
    select distinct on (coalesce(nullif(codigo_unico, ''), 'row-' || source_row)) *
    from source
    order by
        coalesce(nullif(codigo_unico, ''), 'row-' || source_row),
        {{ to_numeric('monto_et_f8') }} desc nulls last
)

select
    nullif(codigo_unico, '') as project_code,
    nullif(codigo_snip, '') as snip_code,
    nombre_inversion as project_name,
    nivel as government_level,
    sector,
    entidad as entity_name,
    sec_ejec as executing_unit_code,
    nombre_uep as executing_unit_name,
    nombre_opmi as planning_office_name,
    nombre_uf as formulating_unit_name,
    nombre_uei as investment_executing_unit_name,
    estado as status,
    situacion as viability_status,
    marco as investment_framework,
    tipo_inversion as investment_type,
    des_modalidad as execution_modality,
    des_tipologia as typology,
    funcion as budget_function,
    programa as budget_program,
    subprograma as budget_subprogram,
    departamento as department,
    provincia as province,
    distrito as district,
    nullif(ubigeo, '') as ubigeo,
    nullif({{ to_numeric('latitud') }}, 0) as latitude,
    nullif({{ to_numeric('longitud') }}, 0) as longitude,
    {{ to_integer('num_habitantes_benef') }} as beneficiaries,

    -- Amounts, in soles
    {{ to_numeric('monto_viable') }} as viable_amount,
    {{ to_numeric('costo_actualizado') }} as updated_cost,
    {{ to_numeric('monto_et_f8') }} as technical_file_amount,
    {{ to_numeric('ctrl_concurr') }} as concurrent_control_amount,
    {{ to_numeric('monto_laudo') }} as arbitration_amount,
    {{ to_numeric('monto_fianza') }} as bond_amount,
    {{ to_numeric('deven_acumul_anio_ant') }} as accrued_until_last_year,
    {{ to_numeric('dev_anio_actual') }} as accrued_current_year,
    {{ to_numeric('pia_anio_actual') }} as opening_budget_current_year,
    {{ to_numeric('pim_anio_actual') }} as modified_budget_current_year,
    {{ to_numeric('certif_anio_actual') }} as certified_current_year,
    {{ to_numeric('comprom_anual_anio_actual') }} as committed_current_year,
    {{ to_numeric('saldo_ejecutar') }} as balance_to_execute,
    {{ to_numeric('pmi_anio_1') }} as multiyear_plan_year_1,
    {{ to_numeric('pmi_anio_2') }} as multiyear_plan_year_2,
    {{ to_numeric('pmi_anio_3') }} as multiyear_plan_year_3,
    {{ to_numeric('pmi_anio_4') }} as multiyear_plan_year_4,

    -- Progress, in percent
    {{ to_numeric('avance_fisico') }} as physical_progress_pct,
    {{ to_numeric('avance_ejecucion') }} as financial_progress_pct,

    -- Dates
    {{ to_local_timestamp('fecha_registro') }}::date as registered_on,
    {{ to_local_timestamp('fecha_viabilidad') }}::date as viability_on,
    {{ to_local_timestamp('fec_ini_ejecucion') }}::date as execution_start_on,
    {{ to_local_timestamp('fec_fin_ejecucion') }}::date as execution_end_on,
    {{ to_local_timestamp('fec_ini_ejec_fisica') }}::date as physical_execution_start_on,
    {{ to_local_timestamp('fec_fin_ejec_fisica') }}::date as physical_execution_end_on,
    {{ to_local_timestamp('ult_fec_decla_estim') }} as last_estimate_declared_at,
    {{ to_local_timestamp('fec_reg_f9') }} as form_9_registered_at,
    {{ yyyymm_to_date('primer_devengado') }} as first_accrual_month,
    {{ yyyymm_to_date('ultimo_devengado') }} as last_accrual_month,

    -- Flags and lifecycle forms
    {{ to_yes_no('registrado_pmi') }} as is_in_multiyear_plan,
    {{ to_yes_no('expediente_tecnico') }} as has_technical_file,
    {{ to_yes_no('informe_cierre') }} as has_closure_report,
    {{ to_yes_no('tiene_f8') }} as has_form_8,
    {{ to_yes_no('tiene_f9') }} as has_form_9,
    {{ to_yes_no('tiene_f12b') }} as has_form_12b,
    {{ to_yes_no('tiene_avan_fisico') }} as has_physical_progress,
    {{ to_yes_no('ind_ioarr_emerg') }} as is_emergency_ioarr,
    etapa_f8 as form_8_stage,
    etapa_f9 as form_9_stage,
    alternativa as selected_alternative,
    {{ to_integer('anio_proceso') }} as process_year,
    _loaded_at
from deduplicated
