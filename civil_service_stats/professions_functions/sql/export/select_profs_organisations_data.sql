
with cs_stats_professions as (
    select *, year * 4 + 1 survey_period
    from civil_service.civil_service_statistics_professions
),
profession_lookup as (
    select id, profession_name, profession_group, profession_category, government_classification
    from civil_service.professions_mapping
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
    cs_stats_professions.id,
    cs_stats_professions.year [Year],
    cs_stats_professions.quarter [Quarter],
    cs_stats_professions.organisation_name [Organisation],
    cs_stats_professions.profession [Profession],
    cs_stats_professions.headcount_fte [FTE],
    profession_lookup.profession_group [Profession group],
    profession_lookup.profession_category [Profession category],
    profession_lookup.government_classification [Government classification],
    case o_vicd_vodg.type 
        when 'Reporting total' then 'All employees'
        else o_vicd_vodg.type
    end [Organisation type],
    case cs_stats_professions.organisation_name
        when 'All employees' then 'All employees'
        when 'Security and Intelligence Services' then 'Security services'
        else o_vicd_vodg.ifg_departmental_group_short_name 
    end [Departmental group],
    case    
        when o_vicd_vodg.is_ifg_core_department = 1 then 'Y'
        else 'N'
    end [IfG core department],
    case cs_stats_professions.organisation_name
        when 'All employees' then 'All employees'
        else vol1.latest_organisation_name
    end [Latest organisation],
    case cs_stats_professions.organisation_name
        when 'All employees' then 'All employees'
        when 'Security and Intelligence Services' then 'Security services'
        else vol2.latest_organisation_short_name
    end [Latest departmental group]
from cs_stats_professions   
    left join o_vicd_vodg on 
        cs_stats_professions.organisation_id = o_vicd_vodg.id and
        cs_stats_professions.survey_period between o_vicd_vodg.start_period and o_vicd_vodg.end_period 
    left join civil_service.vw_organisation_latest vol1 on
        o_vicd_vodg.id = vol1.organisation_id 
    left join civil_service.vw_organisation_latest vol2 on
        o_vicd_vodg.ifg_departmental_group_id = vol2.organisation_id
    left join profession_lookup on
        cs_stats_professions.profession_id = profession_lookup.id
order by
    cs_stats_professions.year,
    cs_stats_professions.organisation_name,
    cs_stats_professions.profession