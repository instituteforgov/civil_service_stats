# %%
"""
    Purpose
        Extract new CS stats leaving cause data and append to database.
    Inputs
        - yaml: leaving_cause_params.yaml
            - Run parameters (source file, sheet names, NA values, year)
        - ods: 'Statistical_tables_-_Civil_Service_Statistics_<yyyy>.ods'
            - Civil Service Statistics source file
    Outputs
        - sql: civil_service.civil_service_statistics_leaving_cause
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

with open("leaving_cause_params.yaml", encoding="utf-8") as f:
    params = yaml.safe_load(f)[-1]

# %%
# Set constants

SOURCE_DIRECTORY = "C:/Users/" + os.getlogin() + "/INSTITUTE FOR GOVERNMENT/Data - General/Civil service/Civil Service Statistics/Source"
SOURCE_FILE = params["source_file"]
SHEET_NAME = params["leaving_cause_sheet_name"]
EXPECTED_SHEET_TITLE = params["expected_leaving_cause_sheet_title"]
EXPECTED_YEAR = params["year"]
NA_VALS = params["na_values"]

# Define expected table layout
HEADER_ROW = 5
FIRST_DATA_ROW = 6
EXPECTED_COL_NAMES = [
    "Civil Service parent department",
    "Civil Service organisation",
    "Headcount of all leavers from the Civil Service for the following cause: Retirement",
    "Headcount of all leavers from the Civil Service for the following cause: Death In Service",
    "Headcount of all leavers from the Civil Service for the following cause: Resignation",
    "Headcount of all leavers from the Civil Service for the following cause: End Of Casual, Period, Conditional Or Provisional Appointment",
    "Headcount of all leavers from the Civil Service for the following cause: Dismissal",
    "Headcount of all leavers from the Civil Service for the following cause: Transfer Of Function To Private Sector",
    "Headcount of all leavers from the Civil Service for the following cause: Secondment To Organisation External To Civil Service",
    "Headcount of all leavers from the Civil Service for the following cause: Transfer To Non-Civil Service Public Sector",
    "Headcount of all leavers from the Civil Service for the following cause: Voluntary Exit Scheme: With Payment",
    "Headcount of all leavers from the Civil Service for the following cause: Voluntary Exit Scheme: With An Unreduced Pension",
    "Headcount of all leavers from the Civil Service for the following cause: Voluntary Exit Scheme: Terms Not Recorded",
    "Headcount of all leavers from the Civil Service for the following cause: Voluntary Redundancy Scheme: With Payment",
    "Headcount of all leavers from the Civil Service for the following cause: Voluntary Redundancy Scheme: With An Unreduced Pension",
    "Headcount of all leavers from the Civil Service for the following cause: Voluntary Redundancy Scheme: Terms Not Recorded",
    "Headcount of all leavers from the Civil Service for the following cause: Compulsory Redundancy Scheme",
    "Headcount of all leavers from the Civil Service for the following cause: Other",
    "Headcount of all leavers from the Civil Service for the following cause: Unknown",
    "Total headcount of all leavers from the Civil Service"
]

# %%
# Set up logger


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
# Load latest release

source = f"{SOURCE_DIRECTORY}/{SOURCE_FILE}"

# Initial read as strigns

df_leavers_str = pd.read_excel(
    source,
    sheet_name=SHEET_NAME,
    header=None,
    dtype=str,
    engine="odf"
)

# Main read
_skip_rows = list(range(HEADER_ROW)) + list(range(HEADER_ROW + 1, FIRST_DATA_ROW))
df_leavers = pd.read_excel(
    source,
    sheet_name=SHEET_NAME,
    skiprows=_skip_rows,
    na_values=NA_VALS,
    engine="odf"
)

logger.info("Starting extraction: %s from '%s'", EXPECTED_YEAR, SOURCE_FILE)

# %%
# Check structure and data quality
_sheet_title = str(df_leavers_str.iloc[1, 0]).strip()
assert _sheet_title == EXPECTED_SHEET_TITLE, (
    f"Unexpected title: {_sheet_title}"
)

_actual_headers = df_leavers_str.iloc[HEADER_ROW].tolist()
assert _actual_headers == EXPECTED_COL_NAMES, (
    f"Column headers do not match expected structure. \n"
    f"  Expected: {EXPECTED_COL_NAMES}\n"
    f"  Actual: {_actual_headers}"
)

used_na_vals = {v for v in NA_VALS if (df_leavers_str == v).any().any()}
unused_na_vals = [v for v in NA_VALS if v not in used_na_vals]
assert not unused_na_vals, f"Unused NA values (remove from params): {unused_na_vals}"

logger.info("Passed all structure and data quality checks")

# %%
# Check for existing records

n = pd.read_sql(
    text(
        """select count(*)
        from civil_service.civil_service_statistics_leaving_cause cs_leavers
        where cs_leavers.year = :year"""
    ),
    con=engine,
    params={"year": EXPECTED_YEAR}
).iloc[0, 0]

assert n == 0, (
     f"{EXPECTED_YEAR} aready has {n} rows in the CS Stats location "
     "table in the database. Remove them before re-running, or check you are "
     "loading the correct release"
)

logger.info("Duplicate check passed — no existing rows for %s", EXPECTED_YEAR)

# %%
# Clean and edit

new_names = [
    "parent_department",
    "organisation_name",
    "Retirement",
    "Death in service",
    "Resingation",
    "End of appointment",
    "Dismissal",
    "Private sector transfer",
    "Secondment",
    "Public sector transfer",
    "Voluntary exit, with payment",
    "Voluntary exit, unreduced pension",
    "Voluntary exit, terms not recorded",
    "Voluntary redundancy, with payment",
    "Voluntary redundancy, unreduced pension",
    "Voluntary redundancy, terms not recorded",
    "Compulsory redundancy",
    "Other",
    "Unknown",
    "Total"
]
col_names = dict(zip(EXPECTED_COL_NAMES, new_names))
df_leavers = df_leavers.rename(columns=col_names)

# %%
# Unpivot
df_leavers = df_leavers.melt(
    id_vars=["parent_department", "organisation_name"],
    var_name="leaving_case",
    value_name="headcount"
).sort_index(kind="stable").reset_index(drop=True)

df_leavers = df_leavers.drop(columns=["parent_department"])

# Handle strings
delete = [
    "(excl. agencies)",
    "(incl. Office of the Advocate General for Scotland)"
]
for s in delete:
    df_leavers["organisation_name"] = df_leavers["organisation_name"].str.replace(s, "", regex=False)

df_leavers["organisation_name"] = df_leavers["organisation_name"].str.strip()
df_leavers = df_leavers[~df_leavers["organisation_name"].str.endswith(" Overall")]

df_leavers["organisation_name"] = df_leavers["organisation_name"].str.replace(
    "Overall Civil Service", "All employees"
)

df_leavers["organisation_name"] = df_leavers["organisation_name"].str.strip()

# %%
# Replace org names with their IfG equivalents

ifg_names = {
    "Advisory, Conciliation and Arbitration Service": "Advisory Conciliation and Arbitration Service",
    "Wilton Park": "Wilton Park Executive Agency",
    "Medicines and Healthcare Products Regulatory Agency": "Medicines and Healthcare products Regulatory Agency",
    "Ministry of Housing, Communities and Local Government": "Ministry of Housing, Communities & Local Government",
    "Office for Standards in Education, Children's Services and Skills": "Office for Standards in Education, Children’s Services and Skills",  # Special apostrophe character
    "Crown Office and Procurator Fiscal Service": "Crown Office and Procurator Fiscal",
    "UK Export Finance": "Export Credits Guarantee Department",
    "Water Services Regulation Authority": "Ofwat"
}

df_leavers["organisation_name"] = df_leavers["organisation_name"].str.replace(ifg_names)

# Add cols
# Add columns
df_leavers.insert(0, "id", [uuid.uuid4() for i in range(len(df_leavers))])
df_leavers.insert(1, "year", EXPECTED_YEAR)
df_leavers.insert(2, "quarter", 1)

# Insert org and function IDs from database
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

df_leavers.insert(
    df_leavers.columns.get_loc("organisation_name"),
    "organisation_id",
    resolve_org_id(df_leavers, df_orgs, quarter_col="quarter")
)

# %%
# Write to database

# Do not run until issues with legacy extraction have been fixed!
"""
df_leavers.to_sql(
    name="civil_service_statistics_leaving_cause",
    con=engine,
    schema="civil_service",
    index=False,
    chunksize=3000,
    if_exists="append",
    dtype={
        "id": UNIQUEIDENTIFIER,
        "year": SMALLINT,
        "quarter": TINYINT,
        "organisation_id": UNIQUEIDENTIFIER,
        "organisation_name": NVARCHAR(100),
        "leaving_cause": NVARCHAR(50),
        "headcount": INT,
    }
)
"""
