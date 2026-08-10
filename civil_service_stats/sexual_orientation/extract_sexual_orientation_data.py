# %%
"""
    Purpose
        Extract new CS stats sexual orientation data and append to database.
    Inputs
        - yaml: sexual_orientation__params.yaml
            - Run parameters (source file, sheet names, NA values, year)
        - ods: 'Statistical_tables_-_Civil_Service_Statistics_<yyyy>.ods'
            - Civil Service Statistics source file
    Outputs
        - sql: civil_service.civil_service_statistics_sexual_orientation
            - Rows corresponding to most recent year's data appended
    Notes
        - New data is appended to the database table, rather than existing rows being modified
        - Run parameters are loaded from params/releases.yaml (last entry used)
        - Carries out the following checks on data:
            - Structure
                - Sheet title matches expected value
                - Column headers match EXPECTED_COL_HEADERS
                - First data row starts at FIRST_DATA_ROW
            - Data quality
                - No unused NA values
            - Before appending
                - No existing rows in the database for the new year
"""

import logging
import os
from pathlib import Path

import ds_utils.database_operations as dbo
import pandas as pd
import yaml
import uuid

from sqlalchemy import INT, NVARCHAR, SMALLINT, text
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER, TINYINT
from civil_service_stats.utils import resolve_org_id

# %%
# Set params

with open('sex_params.yaml') as f:
    params = yaml.safe_load(f)[-1]

# %%
# Set constants

SOURCE_DIRECTORY = "C:/Users/" + os.getlogin() + "/INSTITUTE FOR GOVERNMENT/Data - General/Civil service/Civil Service Statistics/Source"
SOURCE_FILE = params["source_file"]
SHEET_NAME = params["sexual_orientation_sheet_name"]
EXPECTED_SHEET_TITLE = params["expected_sexual_orientation_sheet_title"]
EXPECTED_YEAR = params["year"]
NA_VALS = params["na_values"]

HEADER_ROW = 6
FIRST_DATA_ROW = 7
EXPECTED_COL_NAMES = [
    "Civil Service parent department",
    "Civil Service organisation",
    "Headcount of all civil servants that have declared their sexual orientation as heterosexual or straight",
    "Headcount of all civil servants that have declared their sexual orientation as gay or lesbian",
    "Headcount of all civil servants that have declared their sexual orientation as bisexual",
    "Headcount of all civil servants that have declared as any other sexual orientation",	
    "Headcount of all civil servants actively declaring that they do not want to disclose their sexual orientation",
    "Headcount of all civil servants with an unreported sexual orientation",
    "Total headcount of all civil servants",
    "Headcount of all civil servants with a known sexual orientation",
    "LGBO civil servants as a percentage of known sexual orientation"
]
