
with cs_stats_functions as (
    select *, year * 4 + 1 survey_period
    from civil_service.civil_service_statistics_functions
),
function_lookup as (
    select id, function_name, function_group
    from civil_service.functions_mapping
),
o_vicd_vodg as (
    select
        o.id,
        vodg.organisation_name,
        o.type,
        vicd.is_ifg_core_department,
        vodg.ifg_departmental_group_id,
        vodg.ifg_departmental_group_name,
        vodg.ifg_departmental_group_short_name,
        vodg.start_year,
        vodg.start_quarter,
        vodg.end_year,
        vodg.end_quarter,
        isnull(vodg.start_year * 4 + vodg.start_quarter, 0) start_period,
        isnull(vodg.end_year * 4 + vodg.end_quarter, 2147483647) end_period
    from civil_service.organisation o 
        left join civil_service.vw_ifg_core_departments vicd on
            o.id = vicd.organisation_id
        left join civil_service.vw_organisation_departmental_group vodg on
            o.id = vodg.organisation_id
)

select 
    cs_stats_functions.id,
    cs_stats_functions.year [Year],
    cs_stats_functions.quarter [Quarter],
    cs_stats_functions.organisation_name [Organisation],
    cs_stats_functions.[function] [Function],
    cs_stats_functions.headcount_fte [FTE],
    function_lookup.function_group [Function group],
    case o_vicd_vodg.type 
        when 'Reporting total' then 'All employees'
        else o_vicd_vodg.type
    end [Organisation type],
    case cs_stats_functions.organisation_name
        when 'All employees' then 'All employees'
        when 'Security and Intelligence Services' then 'Security services'
        else o_vicd_vodg.ifg_departmental_group_short_name 
    end [Departmental group],
    case
        when o_vicd_vodg.is_ifg_core_department = 1 then 'Y'
        else 'N'
    end [IfG core department],
    case cs_stats_functions.organisation_name
        when 'All employees' then 'All employees'
        else vol1.latest_organisation_name
    end [Latest organisation],
    case cs_stats_functions.organisation_name
        when 'All employees' then 'All employees'
        when 'Security and Intelligence Services' then 'Security services'
        else vol2.latest_determinate_organisation_short_name
    end [Latest departmental group]
from cs_stats_functions   
    left join o_vicd_vodg on 
        cs_stats_functions.organisation_id = o_vicd_vodg.id and
        cs_stats_functions.survey_period between o_vicd_vodg.start_period and o_vicd_vodg.end_period 
    left join civil_service.vw_organisation_latest vol1 on
        o_vicd_vodg.id = vol1.organisation_id 
    left join civil_service.vw_organisation_latest vol2 on
        o_vicd_vodg.ifg_departmental_group_id = vol2.organisation_id
    left join function_lookup on
        cs_stats_functions.function_id = function_lookup.id
order by 
    cs_stats_functions.year,
    cs_stats_functions.organisation_name,
    cs_stats_functions.[function]
