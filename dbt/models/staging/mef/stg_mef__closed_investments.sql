{{ config(indexes=[{'columns': ['project_code']}]) }}

with source as (
    select * from {{ source('mef', 'mef_closed_investments') }}
)

select
    nullif(codigo_unico, '') as project_code,
    nullif(codigo_snip, '') as snip_code,
    nombre_inversion as project_name,
    nivel as government_level,
    sector,
    entidad as entity_name,
    sec_ejec as executing_unit_code,
    nom_uep as executing_unit_name,
    nom_opmi as planning_office_name,
    nom_uf as formulating_unit_name,
    nom_uei as investment_executing_unit_name,
    estado as status,
    situacion as viability_status,
    marco as investment_framework,
    tipo_inversion as investment_type,
    des_modalidad as execution_modality,
    des_tipologia as typology,
    funcion as budget_function,
    programa as budget_program,
    subprograma as budget_subprogram,
    fuente_financiamiento as funding_source,
    unidad_ope_mant as maintenance_unit,
    departamento as department,
    provincia as province,
    distrito as district,
    nullif(ubigeo, '') as ubigeo,
    nullif({{ to_numeric('latitud') }}, 0) as latitude,
    nullif({{ to_numeric('longitud') }}, 0) as longitude,
    {{ to_integer('beneficiario') }} as beneficiaries,

    -- Amounts, in soles
    {{ to_numeric('monto_viable') }} as viable_amount,
    {{ to_numeric('costo_actualizado') }} as updated_cost,
    {{ to_numeric('control_concurr') }} as concurrent_control_amount,
    {{ to_numeric('monto_laudo') }} as arbitration_amount,
    {{ to_numeric('monto_fianza') }} as bond_amount,
    {{ to_numeric('deven_acumulado') }} as accrued_total,
    {{ to_numeric('total_liquidacion') }} as settlement_amount,

    -- Dates
    {{ to_local_timestamp('fecha_registro') }}::date as registered_on,
    {{ to_local_timestamp('fecha_viabilidad') }}::date as viability_on,
    {{ to_local_timestamp('inicio_ejec_fisica') }}::date as physical_execution_start_on,
    {{ to_local_timestamp('culmina_ejec_fisica') }}::date as physical_execution_end_on,
    {{ to_local_timestamp('fec_ini_oper') }}::date as operation_start_on,
    {{ to_local_timestamp('fec_liquidacion') }}::date as settled_on,
    {{ to_local_timestamp('fec_transferencia') }}::date as transferred_on,
    {{ to_local_timestamp('fec_cierre') }} as closed_at,
    {{ to_local_timestamp('fec_reg_f9') }} as form_9_registered_at,
    {{ yyyymm_to_date('primer_devengado') }} as first_accrual_month,
    {{ yyyymm_to_date('ultimo_devengado') }} as last_accrual_month,

    -- Flags and lifecycle forms
    {{ to_yes_no('expediente_tecnico') }} as has_technical_file,
    {{ to_yes_no('informe_cierre') }} as has_closure_report,
    {{ to_yes_no('tiene_f8') }} as has_form_8,
    {{ to_yes_no('tiene_f9') }} as has_form_9,
    {{ to_yes_no('tiene_f12b') }} as has_form_12b,
    {{ to_yes_no('culminada') }} as is_completed,
    etapa_f9 as form_9_stage,
    des_cierre as closure_description,
    {{ to_integer('anio_proceso') }} as process_year,
    _loaded_at
from source
