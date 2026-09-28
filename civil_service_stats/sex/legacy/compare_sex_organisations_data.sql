-- ReplicaTes the collated organisations data for the CSS sex working file
-- NB: Dates are turned into 'periods' to faciliate temporal joins: period = 4 * year + quarter - e.g. Q1 2025 = 4 * 2025 + 1 = 8101
---- Nulls are set to 0 for start_period and 2^31 - 1 = 2147483647 (max value for SQL INT column) for end_priod
---- survey_period is set to year * 4 + 1, because all CSS data is from quarter 1 of each year

WITH cs_stats_sex AS (
    SELECT 
        *, 
        year * 4 + 1 survey_period
    FROM civil_service.civil_service_statistics_sex
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
    cs_stats_sex.id,
    cs_stats_sex.quarter [Quarter],
    cs_stats_sex.year [Year],
    cs_stats_sex.organisation_name [Organisation],
    cs_stats_sex.sex_and_grade [Sex and Grade],
    cs_stats_sex.headcount [Headcount],
    CASE o_vicd_vodg.type 
        WHEN 'Reporting total' THEN 'All employees'
        ELSE o_vicd_vodg.type
    END [Organisation type],
    CASE cs_stats_sex.organisation_name
        WHEN 'All employees' THEN 'All employees'
        WHEN 'Security and Intelligence Services' THEN 'Security services'
        ELSE o_vicd_vodg.ifg_departmental_group_short_name 
    END [Departmental group],
    CASE cs_stats_sex.organisation_name
        WHEN 'All employees' THEN 'All employees'
        ELSE IIF(
            vol1.latest_organisation_name = 'Indeterminate',
            vol1.latest_determinate_organisation_name,
            vol1.latest_organisation_name
        )
    END [Latest organisation],
    CASE cs_stats_sex.organisation_name
        WHEN 'All employees' THEN 'All employees'
        WHEN 'Security and Intelligence Services' THEN 'Security services'
        ELSE IIF(
            vol2.latest_organisation_short_name = 'Indeterminate',
            vol2.latest_determinate_organisation_short_name,
            vol2.latest_organisation_short_name
        )
    END [Latest departmental group]
FROM cs_stats_sex    
    LEFT JOIN o_vicd_vodg ON 
        cs_stats_sex.organisation_id = o_vicd_vodg.id AND
        cs_stats_sex.survey_period BETWEEN o_vicd_vodg.start_period AND o_vicd_vodg.end_period 
    LEFT JOIN civil_service.vw_organisation_latest vol1 ON
        o_vicd_vodg.id = vol1.organisation_id 
    LEFT JOIN civil_service.vw_organisation_latest vol2 ON
        o_vicd_vodg.ifg_departmental_group_id = vol2.organisation_id
