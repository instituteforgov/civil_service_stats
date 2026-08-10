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

with open('sexual_orientation_params.yaml') as f:
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
        logging.FileHandler(_log_dir / "extract_sexual_orientation_data.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# %%
# Load latest data
source_filepath = f"{SOURCE_DIRECTORY}/{SOURCE_FILE}"

# Initial read as strings
df_s_o_str = pd.read_excel(
    source_filepath,
    sheet_name=SHEET_NAME,
    header=None,
    dtype=str,
    engine="odf"
)

# Full read with structural constants
skip_rows = list(range(HEADER_ROW)) + list(range(HEADER_ROW + 1, FIRST_DATA_ROW))
df_s_o = pd.read_excel(
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
_sheet_tile = str(df_s_o_str.iloc[1, 0]).strip()  # Title is in row 1, not row 0
assert _sheet_tile == EXPECTED_SHEET_TITLE, (
    F"Unexpected title: {_sheet_tile}"
)

# 2: Col headers
_actual_headers = df_s_o_str.iloc[HEADER_ROW].tolist()
assert _actual_headers == EXPECTED_COL_NAMES, (
    f"Column headers do not match expected structure. \n"
    f"  Expected: {EXPECTED_COL_NAMES}\n"
    f"  Actual: {_actual_headers}"
)

# %%
# Check for unused N/A values
used_na_vals = {v for v in NA_VALS if (df_s_o_str == v).any().any()}
unused_na_vals = [v for v in NA_VALS if v not in used_na_vals]
assert not unused_na_vals, f"Unused NA values (remove from params): {unused_na_vals}"

logger.info("Passed structural and data quality checks")

# %%
n_existing = pd.read_sql(
    text(
        """select count(*)
        from civil_service.civil_service_statistics_sexual_orientation cs_s_o
        where cs_s_o.year = :year"""
    ),
    con=engine,
    params={"year": EXPECTED_YEAR}
).iloc[0, 0]

assert n_existing == 0, (
    f"{EXPECTED_YEAR} already has {n_existing} rows in the CS Stats sexual orientation table "
    "in the database. Remove before re-running or check if release number is correct"
)

logger.info("Duplicate check passed - no existing rows for %s", EXPECTED_YEAR)

# %%
# Clean and edit data

# Edit col names
new_names = [
    "parent_department",
    "organisation_name",
    "Heterosexual/Straight",
    "Gay/Lesbian",
    "Bisexual",
    "Other",
    "Not declared",
    "Not reported",
    "All employees",
    "known_orientation",
    "percentage"
]
col_names = dict(zip(EXPECTED_COL_NAMES, new_names))
df_s_o = df_s_o.rename(columns=col_names)
df_s_o = df_s_o.drop(columns=[
    "parent_department", "known_orientation", "percentage"
])

# Unpivot
df_s_o = df_s_o.melt(
    id_vars=["organisation_name"],
    var_name="sexual_orientation",
    value_name="headcount"
).sort_index(kind="stable").reset_index(drop=True)

# Remove whole departmental group data
df_s_o = df_s_o[~df_s_o["organisation_name"].str.endswith(" Overall")]

# Delete unwanted strings
delete_str = [
    "(excl. agencies)",
    "(incl. Office of the Advocate General for Scotland)",
    "[Note 20]"
]
for s in delete_str:
    df_s_o["organisation_name"] = df_s_o["organisation_name"].str.replace(s, "", regex=False)

df_s_o["organisation_name"] = df_s_o["organisation_name"].str.strip()


df_s_o["organisation_name"] = df_s_o["organisation_name"].str.replace(
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

df_s_o["organisation_name"] = df_s_o["organisation_name"].str.replace(ifg_names)

# %%
# Fix row ordering

orientation_order = [
    "Bisexual",
    "Gay/Lesbian",
    "Heterosexual/Straight",
    "Other",
    "Not declared",
    "Not reported",
    "All employees"
]

# dict.fromkeys preserves first-occurrence order and drops duplicates
org_order = list(dict.fromkeys(df_s_o["organisation_name"]))

df_s_o["organisation_name"] = pd.Categorical(df_s_o["organisation_name"], categories=org_order, ordered=True)
df_s_o["sex_and_grade"] = pd.Categorical(df_s_o["sexual_orientation"], categories=orientation_order, ordered=True)
df_s_o = df_s_o.sort_values(["organisation_name", "sexual_orientation"]).reset_index(drop=True)


# %%
# Add info

df_s_o.insert(0, 'id', [uuid.uuid4() for j in range(len(df_s_o))])
df_s_o.insert(1, 'year', EXPECTED_YEAR)
df_s_o.insert(2, 'quarter', 1)

# Insert org IDs
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

df_s_o.insert(
    df_s_o.columns.get_loc("organisation_name"),
    "organisation_id",
    resolve_org_id(df_s_o, df_orgs, quarter_col="quarter")
)

# %%
df_s_o[df_s_o["organisation_id"].isna()]
