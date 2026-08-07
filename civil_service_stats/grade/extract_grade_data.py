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
HEADER_ROW = 5
FIRST_DATA_ROW = 6
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

# %%
# Initialise logger

_log_dir = Path(os.environ["LOCALAPPDATA"]) / "civil_service_stats" / "logs"
_log_dir.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(_log_dir / "extract_grade_data.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# %%
# Connect to research database

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
# Load latest data release

source_filepath = f"{SOURCE_DIRECTORY}/{SOURCE_FILE}"

# Initial read as strings to allow structural checks against params
df_grade_str = pd.read_excel(
    source_filepath,
    sheet_name=SHEET_NAME,
    header=None,
    dtype=str,
    engine="odf"
)

# Then read using layout constants defined above to skip non-data rows
skip_rows = list(range(HEADER_ROW)) + list(range(HEADER_ROW + 1, FIRST_DATA_ROW))
df_grade = pd.read_excel(
    source_filepath,
    sheet_name=SHEET_NAME,
    skiprows=skip_rows,
    na_values=NA_VALS,
    engine="odf"
)

logger.info("Starting extraction: %s from '%s'", EXPECTED_YEAR, SOURCE_FILE)

# %%
# Perform structural checks
# 1: Title
_sheet_title = str(df_grade_str.iloc[1, 0]).strip()  # Sheet title is in row 1 not row 0 ([0,0] is 'Back to contents')
assert _sheet_title == EXPECTED_SHEET_TITLE, (
    f"Unexpected title: {_sheet_title}"
)

# 2: Column headers
_actual_headers = df_grade_str.iloc[HEADER_ROW].tolist()
assert _actual_headers == EXPECTED_COL_NAMES, (
    f"Column headers do not match expected structure. \n"
    f"  Expected: {EXPECTED_COL_NAMES}\n"
    f"  Actual: {_actual_headers}"
)

# %%
# Data quality checks:
# 1: Unused NA values
used_na_vals = {v for v in NA_VALS if (df_grade_str == v).any().any()}
unused_na_vals = [v for v in NA_VALS if v not in used_na_vals]
assert not unused_na_vals, f"Unused NA values (remove from params): {unused_na_vals}"

logger.info("Passed all structure and data quality checks")

# %%
# Duplicate check

n_existing = pd.read_sql(
    text(
        """select count(*)
        from civil_service.civil_service_statistics_grade cs_grade
        where cs_grade.year = :year"""
    ),
    con=engine,
    params={"year": EXPECTED_YEAR}
).iloc[0, 0]

assert n_existing == 0, (
    f"{EXPECTED_YEAR} aready has {n_existing} rows in the CS Stats location "
    "table in the database. Remove them before re-running, or check you are "
    "loading the correct release"
)

logger.info("Duplicate check passed — no existing rows for %s", EXPECTED_YEAR)

# %%
# Clean and edit data

# Edit column names
new_names = [
    "parent_department",
    "organisation_name",
    "Senior Civil Service level",
    "Grades 6 and 7",
    "Senior and Higher Executive Officers",
    "Executive Officers",
    "Administrative Officers and Assistants",
    "Not reported",
    "All employees"
]
col_names = dict(zip(EXPECTED_COL_NAMES, new_names))
df_grade = df_grade.rename(columns=col_names)

# Unpivot table
df_grade = df_grade.melt(
    id_vars=["parent_department", "organisation_name"],
    var_name="grade",
    value_name="headcount_fte",
    ignore_index=False,
).sort_index().reset_index(drop=True)

# Drop irrelevant column
df_grade = df_grade.drop(columns=["parent_department"])

# Drop 'Overall' departmental rows
df_grade = df_grade[~df_grade["organisation_name"].str.endswith(" Overall")]

# Delete superfluous strings
delete_vals = [
    "(excl. agencies)",
    "(incl. Office of the Advocate General for Scotland)"
]
for s in delete_vals:
    df_grade["organisation_name"] = df_grade["organisation_name"].str.replace(s, "", regex=False)

df_grade["organisation_name"] = df_grade["organisation_name"].str.strip()

# Replace 'Overall Civil Service' with 'All employees'
df_grade["organisation_name"] = df_grade["organisation_name"].str.replace(
    "Overall Civil Service", "All employees"
)

# %%
# Replace orgs with their respective IfG names

ifg_names = {
    "Advisory, Conciliation and Arbitration Service": "Advisory Conciliation and Arbitration Service",
    "Wilton Park": "Wilton Park Executive Agency",
    "Medicines and Healthcare Products Regulatory Agency": "Medicines and Healthcare products Regulatory Agency",
    "Ministry of Housing, Communities and Local Government": "Ministry of Housing, Communities & Local Government",
    "Office for Standards in Education, Children's Services and Skills": "Office for Standards in Education, Children’s Services and Skills",
    "Crown Office and Procurator Fiscal Service": "Crown Office and Procurator Fiscal",
    "UK Export Finance": "Export Credits Guarantee Department",
    "Water Services Regulation Authority": "Ofwat"
}

df_grade["organisation_name"] = df_grade["organisation_name"].str.replace(ifg_names)

# %%
# Add UUID, year and quarter columns
df_grade.insert(0, 'id', [uuid.uuid4() for i in range(len(df_grade))])
df_grade.insert(1, 'year', EXPECTED_YEAR)
df_grade.insert(2, 'quarter', 1)

# Insert org IDs from database
df_orgs = pd.read_sql(
    """select
        o.id,
        o.name,
        o.start_year,
        o.start_quarter,
        o.end_year,
        o.end_quarter
    from civil_service.organisation o""",
    engine,
)

df_grade.insert(
    df_grade.columns.get_loc("organisation_name"),
    "organisation_id",
    resolve_org_id(df_grade, df_orgs, quarter_col="quarter")
)

# %%
# Append new rows to database

df_grade.to_sql(
    name="civil_service_statistics_grade",
    con=engine,
    schema="civil_service",
    if_exists="append",
    index=False,
    chunksize=3000,
    dtype={
        "id": UNIQUEIDENTIFIER,
        "quarter": TINYINT,
        "organisation_id": UNIQUEIDENTIFIER,
        "year": SMALLINT,
        "organisation_name": NVARCHAR(100),
        "grade": NVARCHAR(100),
        "headcount_fte": INT
    }
)
