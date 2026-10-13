with cs_stats_faith as (
    select 
        *, 
        year * 4 + 1 survey_period
    from civil_service.civil_service_statistics_faith
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
    cs_stats_faith.id,
    cs_stats_faith.quarter [Quarter],
    cs_stats_faith.year [Year],
    cs_stats_faith.organisation_name [Organisation],
    cs_stats_faith.religion_or_belief [Religion or Belief],
    cs_stats_faith.headcount [Headcount],
    case o_vicd_vodg.type 
        when 'Reporting total' then 'All employees'
        else o_vicd_vodg.type
    end [Organisation type],
    case cs_stats_faith.organisation_name
        when 'All employees' then 'All employees'
        when 'Security and Intelligence Services' then 'Security services'
        else o_vicd_vodg.ifg_departmental_group_short_name 
    end [Departmental group],
    case 
        when o_vicd_vodg.is_ifg_core_department = 1 then 'Y'
        else 'N'
    end [IfG core department],
    case cs_stats_faith.organisation_name
        when 'All employees' then 'All employees'
        else vol1.latest_organisation_name
    end [Latest organisation],
    case cs_stats_faith.organisation_name
        when 'All employees' then 'All employees'
        when 'Security and Intelligence Services' then 'Security services'
        else vol2.latest_organisation_short_name
    end [Latest departmental group]
from cs_stats_faith    
    left join o_vicd_vodg on 
        cs_stats_faith.organisation_id = o_vicd_vodg.id and
        cs_stats_faith.survey_period between o_vicd_vodg.start_period and o_vicd_vodg.end_period 
    left join civil_service.vw_organisation_latest vol1 on
        o_vicd_vodg.id = vol1.organisation_id 
    left join civil_service.vw_organisation_latest vol2 on
        o_vicd_vodg.ifg_departmental_group_id = vol2.organisation_id
order by
    cs_stats_faith.year,
    cs_stats_faith.organisation_name,
    cs_stats_faith.religion_or_belief
