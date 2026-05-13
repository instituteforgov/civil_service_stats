-- Add back-in IfG-derived organisation attributes to the source data
-- NB: 'IfG core department' is recoded to 'Y'/'N' to make it more user-friendly
-- NB: 'Organisation name' is renamed 'Organisation', so that existing PivotTable connections to collated datasets don't break
-- NB: 'Latest IfG departmental group' is renamed 'Latest departmental group', so that existing PivotTable connections to collated datasets don't break

WITH cs_stats_age AS (
    SELECT 
        *, 
        year * 4 + 1 survey_period
    FROM civil_service.civil_service_statistics_age
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
    cs_stats_age.id,
    cs_stats_age.year [Year],
    cs_stats_age.headcount [Headcount],
    cs_stats_age.age [Age],
    cs_stats_age.organisation_name [Organisation],
    o_vicd_vodg.type [Organisation type],
    o_vicd_vodg.ifg_departmental_group_short_name [Departmental group],
    CASE
        WHEN o_vicd_vodg.is_ifg_core_department = 1 THEN 'Y'
        ELSE 'N'
    END [IfG core department],
    vol1.latest_organisation_name [Latest organisation],
    vol2.latest_organisation_short_name [Latest departmental group]
FROM cs_stats_age    
    LEFT JOIN o_vicd_vodg ON 
        cs_stats_age.organisation_id = o_vicd_vodg.id AND
        cs_stats_age.survey_period BETWEEN o_vicd_vodg.start_period AND o_vicd_vodg.end_period 
    LEFT JOIN civil_service.vw_organisation_latest vol1 ON
        o_vicd_vodg.id = vol1.organisation_id 
    LEFT JOIN civil_service.vw_organisation_latest vol2 ON
        o_vicd_vodg.ifg_departmental_group_id = vol2.organisation_id


