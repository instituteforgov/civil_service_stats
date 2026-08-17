# %%
"""
    Purpose
        Extract new CS stats professions data and append to database.
    Inputs
        - yaml: professions_params.yaml
            - Run parameters (source file, sheet names, NA values, year)
        - ods: 'Statistical_tables_-_Civil_Service_Statistics_<yyyy>.ods'
            - Civil Service Statistics source file
    Outputs
        - sql: civil_service.civil_service_statistics_professions
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
from civil_service_stats.utils import resolve_org_id, resolve_profession_id

# %%
# Set parameters

with open("professions_params.yaml") as f:
    params = yaml.safe_load(f)[-1]

# %%
# Constants

SOURCE_DIRECTORY = "C:/Users/" + os.getlogin() + "/INSTITUTE FOR GOVERNMENT/Data - General/Civil service/Civil Service Statistics/Source"
SOURCE_FILE = params["source_file"]
SHEET_NAME = params["professions_sheet_name"]
EXPECTED_SHEET_TITLE = params["expected_professions_sheet_title"]
EXPECTED_YEAR = params["year"]
NA_VALS = params["na_values"]

# Table structure
HEADER_ROW = 5
FIRST_DATA_ROW = 6
EXPECTED_COL_NAMES = [
    "Civil Service parent department",
    "Civil Service organisation",
    "Full-time equivalent (FTE) of all civil servants working in the Actuary profession",
    "Full-time equivalent (FTE) of all civil servants working in the Clinical profession",
    "Full-time equivalent (FTE) of all civil servants working in the Commercial profession",
    "Full-time equivalent (FTE) of all civil servants working in the Communications profession",
    "Full-time equivalent (FTE) of all civil servants working in the Corporate Finance profession",
    "Full-time equivalent (FTE) of all civil servants working in the Counter Fraud profession",
    "Full-time equivalent (FTE) of all civil servants working in the Cyber profession",
    "Full-time equivalent (FTE) of all civil servants working in the Debt profession",
    "Full-time equivalent (FTE) of all civil servants working in the Digital and Data profession",
    "Full-time equivalent (FTE) of all civil servants working in the Economics profession",
    "Full-time equivalent (FTE) of all civil servants working in the Finance profession",
    "Full-time equivalent (FTE) of all civil servants working in the Grants profession",
    "Full-time equivalent (FTE) of all civil servants working in the Geography profession",
    "Full-time equivalent (FTE) of all civil servants working in the Human Resources profession",
    "Full-time equivalent (FTE) of all civil servants working in the Inspector of Education and Training profession",
    "Full-time equivalent (FTE) of all civil servants working in the Intelligence Analysis profession",
    "Full-time equivalent (FTE) of all civil servants working in the Internal Audit profession",
    "Full-time equivalent (FTE) of all civil servants working in the Knowledge and Information Management profession",
    "Full-time equivalent (FTE) of all civil servants working in the Legal profession",
    "Full-time equivalent (FTE) of all civil servants working in the Occupational Psychology Profession",
    "Full-time equivalent (FTE) of all civil servants working in the Operational Delivery profession",
    "Full-time equivalent (FTE) of all civil servants working in the Operational Research profession",
    "Full-time equivalent (FTE) of all civil servants working in the Planning profession",
    "Full-time equivalent (FTE) of all civil servants working in the Planning Inspectors profession",
    "Full-time equivalent (FTE) of all civil servants working in the Policy profession",
    "Full-time equivalent (FTE) of all civil servants working in the Project Delivery profession",
    "Full-time equivalent (FTE) of all civil servants working in the Property profession",
    "Full-time equivalent (FTE) of all civil servants working in the Risk Management profession",
    "Full-time equivalent (FTE) of all civil servants working in the Science and Engineering profession",
    "Full-time equivalent (FTE) of all civil servants working in the Security profession",
    "Full-time equivalent (FTE) of all civil servants working in the Social Research profession",
    "Full-time equivalent (FTE) of all civil servants working in the Statistics profession",
    "Full-time equivalent (FTE) of all civil servants working in the Tax profession",
    "Full-time equivalent (FTE) of all civil servants working in the Veterinarian profession",
    "Full-time equivalent (FTE) of all civil servants working in any other profession",
    "Full-time equivalent (FTE) of all civil servants with no reported profession",
    "Total full-time equivalent (FTE) of all civil servants",
]

# %%
# Set up logging

_log_dir = Path(os.environ["LOCALAPPDATA"]) / "civil_service_stats" / "logs"
_log_dir.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(_log_dir / "extract_professions_data.log", encoding="utf-8"),
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
df_profs_str = pd.read_excel(
    source_filepath,
    sheet_name=SHEET_NAME,
    header=None,
    dtype=str,
    engine="odf"
)

# Full read
_skip_rows = list(range(HEADER_ROW)) + list(range(HEADER_ROW + 1, FIRST_DATA_ROW))
df_profs = pd.read_excel(
    source_filepath,
    sheet_name=SHEET_NAME,
    skiprows=_skip_rows,
    na_values=NA_VALS,
    engine="odf"
)

logger.info("Starting extraction: %s from '%s'", EXPECTED_YEAR, SOURCE_FILE)

# %%
# Check structure

_sheet_title = str(df_profs_str.iloc[1, 0]).strip()
assert _sheet_title == EXPECTED_SHEET_TITLE, (
    f"Unexpected sheet title: {_sheet_title}"
)

_headers = df_profs_str.iloc[HEADER_ROW].to_list()
assert _headers == EXPECTED_COL_NAMES, (
    f"Column headers do not match expected strucuture:\n"
    f"Expected: {EXPECTED_COL_NAMES}\n"
    f"Actual: {_headers}"
)

# %%
# Check data quality
used_na_vals = {v for v in NA_VALS if (df_profs_str == v).any().any()}
unused_na_vals = [v for v in NA_VALS if v not in used_na_vals]
assert not unused_na_vals, f"Unused NA values - remove from params: {unused_na_vals}"

# %%
# Check for exisiting records in database

n = pd.read_sql(
    text(
        """select count(*)
        from civil_service.civil_service_statistics_professions cs_profs
        where cs_profs.year = :year"""
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
# Clean and edit data

new_names = [
    "parent_department",
    "organisation_name",
    "Actuary",
    "Clinical",
    "Commercial",
    "Communications",
    "Corporate Finance",
    "Counter Fraud",
    "Cyber",
    "Debt",
    "Digital and Data",
    "Economics",
    "Finance",
    "Grants",
    "Geography",
    "Human Resources",
    "Inspector of Education and Training",
    "Intelligence Analysis",
    "Internal Audit",
    "Knowledge and Information Management",
    "Legal",
    "Occupational Psychology",
    "Operational Delivery",
    "Operational Research",
    "Planning",
    "Planning Inspectors",
    "Policy",
    "Project Delivery",
    "Property",
    "Risk Management",
    "Science and Engineering",
    "Security",
    "Social Research",
    "Statistics",
    "Tax",
    "Veterinarian",
    "Other",
    "Not reported",
    "Total"
]
assert len(new_names) == len(EXPECTED_COL_NAMES), (
    f"Mismatch: source has {len(EXPECTED_COL_NAMES)} columns, but only {len(new_names)} new col names given"
)

col_names = dict(zip(EXPECTED_COL_NAMES, new_names))
df_profs = df_profs.rename(columns=col_names)

# %%
# Unpivot
df_profs = df_profs.melt(
    id_vars=["parent_department", "organisation_name"],
    var_name="profession",
    value_name="headcount_fte"
).sort_index(kind="stable").reset_index(drop=True)

df_profs = df_profs.drop(columns=["parent_department"])

# Handle strings
delete = [
    "(excl. agencies)",
    "(incl. Office of the Advocate General for Scotland)",
    "[Note 20]",
    "[Note 21]",
    "[Note 25]",
    "[Note 26]"
]
for x in delete:
    df_profs["organisation_name"] = df_profs["organisation_name"].str.replace(x, "", regex=False)

df_profs["organisation_name"] = df_profs["organisation_name"].str.strip()
df_profs = df_profs[~df_profs["organisation_name"].str.endswith(" Overall")]

df_profs["organisation_name"] = df_profs["organisation_name"].str.replace(
    "Overall Civil Service", "All employees"
)

df_profs["organisation_name"] = df_profs["organisation_name"].str.strip()

# %%
# Replace org names with their IfG equivalents

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

df_profs["organisation_name"] = df_profs["organisation_name"].str.replace(ifg_names)

# Add cols
# Add columns
df_profs.insert(0, "id", [uuid.uuid4() for i in range(len(df_profs))])
df_profs.insert(1, "year", EXPECTED_YEAR)
df_profs.insert(2, "quarter", 1)

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

df_professions = pd.read_sql(
    "SELECT id, profession_name AS profession "
    "FROM civil_service.professions_mapping",
    engine
)

df_profs.insert(
    df_profs.columns.get_loc("organisation_name"),
    "organisation_id",
    resolve_org_id(df_profs, df_orgs, quarter_col="quarter")
)

df_profs.insert(
    df_profs.columns.get_loc("profession"),
    "profession_id",
    resolve_profession_id(df_profs, df_professions)
)

# %%
# Write to DB

df_profs.to_sql(
    name="civil_service_statistics_professions",
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
