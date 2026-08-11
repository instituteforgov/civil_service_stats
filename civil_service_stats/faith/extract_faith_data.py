# %%
"""
    Purpose
        Extract new CS stats faith and religion data and append to database.
    Inputs
        - yaml: faith_params.yaml
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
# Read params

with open("faith_params.yaml", encoding="utf-8") as f:
    params = yaml.safe_load(f)[-1]

# %%
# Set constants

SOURCE_DIRECTORY = "C:/Users/" + os.getlogin() + "/INSTITUTE FOR GOVERNMENT/Data - General/Civil service/Civil Service Statistics/Source"
SOURCE_FILE = params["source_file"]
SHEET_NAME = params["faith_sheet_name"]
EXPECTED_SHEET_TITLE = params["expected_faith_sheet_title"]
EXPECTED_YEAR = params["year"]
NA_VALS = params["na_values"]

# Define expected table layout
HEADER_ROW = 6
FIRST_DATA_ROW = 7
EXPECTED_COL_NAMES = [
    "Civil Service parent department",
    "Civil Service organisation",
    "Headcount of all civil servants declaring as Christian",
    "Headcount of all civil servants declaring as Buddhist",
    "Headcount of all civil servants declaring as Hindu",
    "Headcount of all civil servants declaring as Jewish",
    "Headcount of all civil servants declaring as Muslim",
    "Headcount of all civil servants declaring as Sikh",
    "Headcount of all civil servants declaring as any other religion",
    "Headcount of all civil servants that have declared that they are not affiliated with any religion or belief",
    "Headcount of all civil servants actively declaring they do not want to disclose their religion or belief",
    "Headcount of all civil servants who have not made an active declaration about their religion or belief",
    "Total headcount of all civil servants",
    "Headcount of all civil servants with a known religion or belief",
    "Percentage of civil servants with a known religion or belief"
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
        logging.FileHandler(_log_dir / "extract_faith_data.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)
