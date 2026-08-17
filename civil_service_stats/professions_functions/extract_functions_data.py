# %%
"""
    Purpose
        Extract new CS stats functions data and append to database.
    Inputs
        - yaml: functions_params.yaml
            - Run parameters (source file, sheet names, NA values, year)
        - ods: 'Statistical_tables_-_Civil_Service_Statistics_<yyyy>.ods'
            - Civil Service Statistics source file
    Outputs
        - sql: civil_service.civil_service_statistics_functions
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
from civil_service_stats.utils import resolve_org_id, resolve_function_id

# %%
# Set parameters

with open("functions_params.yaml") as f:
    params = yaml.safe_load(f)[-1]

# %%
# Constants

SOURCE_DIRECTORY = "C:/Users/" + os.getlogin() + "/INSTITUTE FOR GOVERNMENT/Data - General/Civil service/Civil Service Statistics/Source"
SOURCE_FILE = params["source_file"]
SHEET_NAME = params["functions_sheet_name"]
EXPECTED_SHEET_TITLE = params["expected_functions_sheet_title"]
EXPECTED_YEAR = params["year"]
NA_VALS = params["na_values"]

# Table structure
HEADER_ROW = 5
FIRST_DATA_ROW = 6
EXPECTED_COL_NAMES = [
    "Civil Service parent department",
    "Civil Service organisation",
    "Full-time equivalent (FTE) of all civil servants working in the Analysis function",
    "Full-time equivalent (FTE) of all civil servants working in the Commercial function",
    "Full-time equivalent (FTE) of all civil servants working in the Communications function",
    "Full-time equivalent (FTE) of all civil servants working in the Counter Fraud function",
    "Full-time equivalent (FTE) of all civil servants working in the Debt function",
    "Full-time equivalent (FTE) of all civil servants working in the Digital and Data function",
    "Full-time equivalent (FTE) of all civil servants working in the Finance function",
    "Full-time equivalent (FTE) of all civil servants working in the Grants function",
    "Full-time equivalent (FTE) of all civil servants working in the People function",
    "Full-time equivalent (FTE) of all civil servants working in the Internal Audit function",
    "Full-time equivalent (FTE) of all civil servants working in the Legal function",
    "Full-time equivalent (FTE) of all civil servants working in the Project Delivery function",
    "Full-time equivalent (FTE) of all civil servants working in the Property function",
    "Full-time equivalent (FTE) of all civil servants working in the Security function",
    "Full-time equivalent (FTE) of all civil servants not working in a core function",
    "Full-time equivalent (FTE) of all civil servants with an unreported function",
    "Total full-time equivalent (FTE) of all civil servants"
]

# %%
# Set up logging

_log_dir = Path(os.environ["LOCALAPPDATA"]) / "civil_service_stats" / "logs"
_log_dir.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(_log_dir / "extract_functions_data.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

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
# Load latest data release
source_filepath = f"{SOURCE_DIRECTORY}/{SOURCE_FILE}"

# Read file as strings
df_funcs_str = pd.read_excel(
    source_filepath,
    sheet_name=SHEET_NAME,
    header=None,
    dtype=str,
    engine="odf"
)

# Full read
_skip_rows = list(range(HEADER_ROW)) + list(range(HEADER_ROW + 1, FIRST_DATA_ROW))
df_funcs = pd.read_excel(
    source_filepath,
    sheet_name=SHEET_NAME,
    skiprows=_skip_rows,
    na_values=NA_VALS,
    engine="odf"
)

logger.info("Starting extraction: %s from '%s'", EXPECTED_YEAR, SOURCE_FILE)

# %%
# Check structure

_sheet_title = str(df_funcs_str.iloc[1, 0]).strip()
assert _sheet_title == EXPECTED_SHEET_TITLE, (
    f"Unexpected sheet title: {_sheet_title}"
)

_headers = df_funcs_str.iloc[HEADER_ROW].to_list()
assert _headers == EXPECTED_COL_NAMES, (
    f"Column headers do not match expected strucuture:\n"
    f"Expected: {EXPECTED_COL_NAMES}\n"
    f"Actual: {_headers}"
)

# %%
# Check data quality
used_na_vals = {v for v in NA_VALS if (df_funcs_str == v).any().any()}
unused_na_vals = [v for v in NA_VALS if v not in used_na_vals]
assert not unused_na_vals, f"Unused NA values - remove from params: {unused_na_vals}"

# %%
# Check for exisiting records in database

n = pd.read_sql(
    text(
        """select count(*)
        from civil_service.civil_service_statistics_functions cs_funcs
        where cs_funcs.year = :year"""
    ),
    con=engine,
    params={"year": EXPECTED_YEAR}
).iloc[0, 0]

assert n == 0, (
    f"There are already {n} rows for {EXPECTED_YEAR} in the database."
    "Remove before re-running, or check release year"
)

logger.info("Passed structure and data quality tests")

# %%
# clean and edit data

new_names = [
    "parent_department",
    "organisation_name",
    "Analysis",
    "Commercial",
    "Communications",
    "Counter Fraud",
    "Debt",
    "Government Digital and Data",
    "Finance",
    "Grants Management",
    "People",
    "Internal Audit",
    "Legal",
    "Project Delivery",
    "Property",
    "Security",
    "No function",
    "Not reported",
    "Total"
]

assert len(new_names) == len(EXPECTED_COL_NAMES), (
    f"Mismatch: source has f{len(EXPECTED_COL_NAMES)} column headers but name reassignment list has {len(new_names)}"
)

col_names = dict(zip(EXPECTED_COL_NAMES, new_names))
df_funcs = df_funcs.rename(columns=col_names)

# Unpivot
df_funcs = df_funcs.melt(
    id_vars=["parent_department", "organisation_name"],
    var_name="function",
    value_name="headcount_fte"
).sort_index(kind="stable").reset_index(drop=True)

df_funcs = df_funcs.drop(columns="parent_department")
df_funcs = df_funcs[~df_funcs["organisation_name"].str.endswith(" Overall")]

# Handle strings
delete = [
    "(excl. agencies)",
    "(incl. Office of the Advocate General for Scotland)",
    "[Note 20]",
    "[Note 15]",
    "[Note 16]"
]
for k in delete:
    df_funcs["organisation_name"] = df_funcs["organisation_name"].str.replace(k, "", regex=False)

df_funcs["organisation_name"] = df_funcs["organisation_name"].str.replace(
    "Overall Civil Service", "All employees"
)

df_funcs["organisation_name"] = df_funcs["organisation_name"].str.strip()

# %%
# Replace orgs with IfG names

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

df_funcs["organisation_name"] = df_funcs["organisation_name"].str.replace(ifg_names)

# Add columns
df_funcs.insert(0, "id", [uuid.uuid4() for i in range(len(df_funcs))])
df_funcs.insert(1, "year", EXPECTED_YEAR)
df_funcs.insert(2, "quarter", 1)

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

df_functions = pd.read_sql(
    "SELECT id, function_name AS [function] "
    "FROM civil_service.functions_mapping",
    engine
)

df_funcs.insert(
    df_funcs.columns.get_loc("organisation_name"),
    "organisation_id",
    resolve_org_id(df_funcs, df_orgs, quarter_col="quarter")
)

df_funcs.insert(
    df_funcs.columns.get_loc("function"),
    "function_id",
    resolve_function_id(df_funcs, df_functions)
)

# %%
# Write to database

df_funcs.to_sql(
    name="civil_service_statistics_functions",
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
        "function": NVARCHAR(50),
        "headcount_fte": INT,
    }
)
