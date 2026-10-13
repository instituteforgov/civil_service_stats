-- Add back-in IfG-derived organisation attributes to the source data
-- NB: 'IfG core department' is recoded to 'Y'/'N' to make it more user-friendly
-- NB: 'Organisation name' is renamed 'Organisation', so that existing PivotTable connections to collated datasets don't break
-- NB: 'Latest IfG departmental group' is renamed 'Latest departmental group', so that existing PivotTable connections to collated datasets don't break

with cs_stats_age as (
    select 
        *, 
        year * 4 + 1 survey_period
    from civil_service.civil_service_statistics_age
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
    cs_stats_age.id,
    cs_stats_age.year [Year],
    cs_stats_age.organisation_name [Organisation],
    cs_stats_age.headcount [Headcount],
    cs_stats_age.age [Age],
    case o_vicd_vodg.type 
        when 'Reporting total' then 'All employees'
        else o_vicd_vodg.type
    end [Organisation type],
    case cs_stats_age.organisation_name
        when 'All employees' then 'All employees'
        when 'Security and Intelligence Services' then 'Security services'
        else o_vicd_vodg.ifg_departmental_group_short_name 
    end [Departmental group],
    case
        when o_vicd_vodg.is_ifg_core_department = 1 then 'Y'
        else 'N'
    end [IfG core department],
    case cs_stats_age.organisation_name
        when 'All employees' then 'All employees'
        else vol1.latest_organisation_name
    end [Latest organisation],
    case cs_stats_age.organisation_name
        when 'All employees' then 'All employees'
        when 'Security and Intelligence Services' then 'Security services'
        else vol2.latest_organisation_short_name
    end [Latest departmental group]
from cs_stats_age    
    left join o_vicd_vodg on 
        cs_stats_age.organisation_id = o_vicd_vodg.id and
        cs_stats_age.survey_period between o_vicd_vodg.start_period and o_vicd_vodg.end_period 
    left join civil_service.vw_organisation_latest vol1 on
        o_vicd_vodg.id = vol1.organisation_id 
    left join civil_service.vw_organisation_latest vol2 on
        o_vicd_vodg.ifg_departmental_group_id = vol2.organisation_id
order by
    cs_stats_age.year,
    cs_stats_age.organisation_name

