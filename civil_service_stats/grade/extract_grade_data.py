# %%
"""
    Purpose
        Extract new CS stats grade data and append to database.
    Inputs
        - yaml: params/grade_releases.yaml
            - Run parameters (source file, sheet names, NA values, year)
        - ods: 'Statistical_tables_-_Civil_Service_Statistics_<yyyy>.ods'
            - Civil Service Statistics source file
    Outputs
        - sql: civil_service.civil_service_statistics_grade
            - Rows corresponding to most recent year's data appended
    Notes
        - New data is appended to the database table, rather than existing rows being modified
        - Run parameters are loaded from params/releases.yaml (last entry used)
        - Carries out the following checks on data:
            - Structure
                - Sheet title matches expected value
                - Column headers match EXPECTED_COL_HEADERS
                - Latest year column matches EXPECTED_YEAR
                - First data row starts at FIRST_DATA_ROW with measure EXPECTED_FIRST_MEASURE
                - Note references only appear in the Measure notes column
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

from sqlalchemy import DECIMAL, NVARCHAR, SMALLINT
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from civil_service_stats.utils import resolve_org_id

# %%
# Read in parameters from yaml file

with open("grade_params.yaml", encoding="utf-8") as f:
    params = yaml.safe_load(f)[-1]

# %%
# Set constants

SOURCE_DIRECTORY = "C:/Users/" + os.getlogin() + "/INSTITUTE FOR GOVERNMENT/Data - General/Civil service/Civil Service Statistics/Source"
SOURCE_FILE = params["source_file"]
SHEET_NAME = params["grade_sheet_name"]
EXPECTED_SHEET_TITLE = params["expected_grade_sheet_title"]
EXPECTED_YEAR = params["year"]
NA_VALS = params["na_values"]

# Define expected table layout
HEADER_ROW = 6
EXPECTED_COL_NAMES = [
    "Civil Service parent department",
    "Civil Service organisation",
    "Full-time equivalent (FTE) of all civil servants working at Senior Civil Service level",
    "Full-time equivalent (FTE) of all civil servants working at Grade 6 or Grade 7 level",
    "Full-time equivalent (FTE) of all civil servants working at Senior or Higher Executive Officer level",
    "Full-time equivalent (FTE) of all civil servants working at Executive Officer level",
    "Full-time equivalent (FTE) of all civil servants working at Administrative Assistant or Administrative Officer level",
    "Full-time equivalent (FTE) of all civil servants with an unreported grade",
    "Full-time equivalent (FTE) of all civil servants"
]

FIRST_DATA_ROW = 7

# %%
# Initialise logger

Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler("logs/extract_grade_data.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)
