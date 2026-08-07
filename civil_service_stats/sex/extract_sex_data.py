# %%
"""
    Purpose
        Extract new CS stats sex by grade data and append to database.
    Inputs
        - yaml: sex_params.yaml
            - Run parameters (source file, sheet names, NA values, year)
        - ods: 'Statistical_tables_-_Civil_Service_Statistics_<yyyy>.ods'
            - Civil Service Statistics source file
    Outputs
        - sql: civil_service.civil_service_statistics_age
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
SHEET_NAME = params["sex_sheet_name"]
EXPECTED_SHEET_TITLE = params["expected_sex_sheet_title"]
EXPECTED_YEAR = params["year"]
NA_VALS = params["na_values"]

HEADER_ROW = 5
FIRST_DATA_ROW = 6
EXPECTED_COL_NAMES = [
    "Civil Service parent department",
    "Civil Service organisation",
    "Headcount of all male civil servants working at Senior Civil Service Level",
    "Headcount of all male civil servants working at Grade 6 or Grade 7 level",
    "Headcount of all male civil servants working at Senior or Higher Executive Officer level",
    "Headcount of all male civil servants working at Executive Officer level",
    "Headcount of all male civil servants working at Administrative Assistant or Administrative Officer level",
    "Headcount of male civil servants with an unreported grade",
    "Total headcount of all male civil servants",
    "Headcount of all female civil servants working at Senior Civil Service Level",
    "Headcount of all female civil servants working at Grade 6 or Grade 7 level",
    "Headcount of all female civil servants working at Senior or Higher Executive Officer level",
    "Headcount of all female civil servants working at Executive Officer level",
    "Headcount of all female civil servants working at Administrative Assistant or Administrative Officer level",
    "Headcount of female civil servants with an unreported grade",
    "Total headcount of all female civil servants",
    "Headcount of all civil servants with an unknown sex working at Senior Civil Service Level",
    "Headcount of all civil servants with an unknown sex working at Grade 6 or Grade 7 level",
    "Headcount of all civil servants with an unknown sex working at Senior or Higher Executive Officer level",
    "Headcount of all civil servants with an unknown sex working at Executive Officer level",
    "Headcount of all civil servants with an unknown sex working at Administrative Assistant or Administrative Officer level",
    "Headcount of civil servants with an unknown sex with an unreported grade",
    "Total headcount of all civil servants with an unknown sex",
]

# %%
# Connect to database

engine = dbo.connect_sql_db(
    driver="pyodbc",
    driver_version=os.environ["ODBC_DRIVER"],
    dialect="mssql",
    server=os.environ["ODBC_SERVER"],
    database=os.environ["ODBC_DATABASE"],
    authentication=os.environ["ODBC_AUTHENTICATION"],
    username=os.environ["AZURE_CLIENT_ID"],
    password=os.environ["AZURE_CLIENT_SECRET"],
)

# %%
# Set up logging

_log_dir = Path(os.environ["LOCALAPPDATA"]) / "civil_service_stats" / "logs"
_log_dir.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(_log_dir / "extract_ethnicity_data.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)
