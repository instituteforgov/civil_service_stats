-- Replicates collated data calculations for the Civil Service Statistics age data working file

-- NB: This turns all dates into 'periods', to facilitate temporal joins. These are defined as year * 4 + quarter, so e.g. 2020 Q4 becomes 2020 * 4 + 4 = 8084, 
-- -- with nulls set to 0 for start_period and the maximum integer that can be held in a SQL int column for end_period

-- NB: survey_period in the CS Stats age data is set to year * 4 + 1, because all such data is from quarter 1 of each year
-- NB: Temporal joins use _between_, which includes both endpoints, because start/end year/quarters in civil_service.organisation are inclusive and non-overlapping.
----  I.e. if an organisation ends in period N, it's successor starts in period N + 1

-- NB: Join between `civil_service.organisation` and `civil_service.vw_organisation_departmental_group` needs to be a left join as
---- rganisation aggregations and disaggregations don't feature in `civil_service.vw_organisation_departmental_group`, by design

-- NB: `case` statements do two things:
    -- 1. `Organisation` column: Add ' - <yyyy> iteration' strings that were cleaned as part of the extraction and loading of the data into the database back in to organisation names,
    ---- to facilitate comparison between the collated data generated using this script and that in the original working file
    -- 2. (Specific to the CSPS organisations data) `Departmental group`, `Latest organisation`, `Latest IfG departmental group` columns: 
    ----Handle organisations with type 'Aggregation' or 'Disaggregation' that feature in the source data, as these don't feature in civil_service.vw_organisation_departmental_group and civil_service.vw_organisation_latest

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
        isnull(vodg.start_year * 4 + vodg.start_quarter, 0) start_period,
        isnull(vodg.end_year * 4 + vodg.end_quarter, 2147483647) end_period
    FROM civil_service.organisation o 
        LEFT JOIN civil_service.vw_ifg_core_departments vicd ON
            o.id = vicd.organisation_id
        LEFT JOIN civil_service.vw_organisation_departmental_group vodg ON
            o.id = vodg.organisation_id
)

SELECT 
    cs_stats_age.id,
    cs_stats_age.year,
    cs_stats_age.organisation_name [Organisation],
    o_vicd_vodg.type [Organisation type],
    o_vicd_vodg.ifg_departmental_group_short_name [Departmental group],
    CASE
        WHEN o_vicd_vodg.is_ifg_core_department = 1 THEN 'Y'
        ELSE 'N'
    END [IfG core department]


FROM  cs_stats_age    
    LEFT JOIN o_vicd_vodg ON 
        cs_stats_age.id = o_vicd_vodg.id 
        AND
        (cs_stats_age.survey_period BETWEEN o_vicd_vodg.start_period AND o_vicd_vodg.end_period)
;