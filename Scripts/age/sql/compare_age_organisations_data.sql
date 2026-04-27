-- ReplicaTes the collated organisations data for the CSS age working file
-- NB: Dates are turned into 'periods' to faciliate temporal joins: period = 4 * year + quarter - e.g. Q1 2025 = 4 * 2025 + 1 = 8101
---- Nulls are set to 0 for start_period and 2^31 - 1 = 2147483647 (max value for SQL INT column) for end_priod
---- survey_period is set to year * 4 + 1, because all CSS data is from quarter 1 of each year

