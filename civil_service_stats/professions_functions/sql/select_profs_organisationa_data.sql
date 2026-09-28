
WITH cs_stats_professions AS (
    SELECT *, year * 4 + 1 survey_period
    FROM civil_service.civil_service_statistics_professions
),
profession_lookup AS (
    SELECT id, profession_name, profession_group, profession_category, government_classification
    FROM civil_service.professions_mapping
),
o_vicd_vodg AS (
    SELECT
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
        ISNULL(vodg.start_year * 4 + vodg.start_quarter, 0) start_period,
        ISNULL(vodg.end_year * 4 + vodg.end_quarter, 2147483647) end_period
    FROM civil_service.organisation o 
        LEFT JOIN civil_service.vw_ifg_core_departments vicd ON
            o.id = vicd.organisation_id
        LEFT JOIN civil_service.vw_organisation_departmental_group vodg ON
            o.id = vodg.organisation_id
)

SELECT 
    cs_stats_professions.id,
    cs_stats_professions.year [Year],
    cs_stats_professions.quarter [Quarter],
    cs_stats_professions.organisation_name [Organisation],
    cs_stats_professions.profession [Profession],
    cs_stats_professions.headcount_fte [FTE],
    profession_lookup.profession_group [Profession group],
    profession_lookup.profession_category [Profession category],
    profession_lookup.government_classification [Government classification],
    CASE o_vicd_vodg.type 
        WHEN 'Reporting total' THEN 'All employees'
        ELSE o_vicd_vodg.type
    END [Organisation type],
    CASE cs_stats_professions.organisation_name
        WHEN 'All employees' THEN 'All employees'
        WHEN 'Security and Intelligence Services' THEN 'Security services'
        ELSE o_vicd_vodg.ifg_departmental_group_short_name 
    END [Departmental group],
    CASE    
        WHEN o_vicd_vodg.is_ifg_core_department = 1 THEN 'Y'
        ELSE 'N'
    END [IfG core department],
    CASE cs_stats_professions.organisation_name
        WHEN 'All employees' THEN 'All employees'
        ELSE vol1.latest_organisation_name
    END [Latest organisation],
    CASE cs_stats_professions.organisation_name
        WHEN 'All employees' THEN 'All employees'
        WHEN 'Security and Intelligence Services' THEN 'Security services'
        ELSE vol2.latest_organisation_short_name
    END [Latest departmental group]
FROM cs_stats_professions   
    LEFT JOIN o_vicd_vodg ON 
        cs_stats_professions.organisation_id = o_vicd_vodg.id AND
        cs_stats_professions.survey_period BETWEEN o_vicd_vodg.start_period AND o_vicd_vodg.end_period 
    LEFT JOIN civil_service.vw_organisation_latest vol1 ON
        o_vicd_vodg.id = vol1.organisation_id 
    LEFT JOIN civil_service.vw_organisation_latest vol2 ON
        o_vicd_vodg.ifg_departmental_group_id = vol2.organisation_id
    LEFT JOIN profession_lookup ON
        cs_stats_professions.profession_id = profession_lookup.id
ORDER BY
    cs_stats_professions.year,
    cs_stats_professions.organisation_name,
    cs_stats_professions.profession