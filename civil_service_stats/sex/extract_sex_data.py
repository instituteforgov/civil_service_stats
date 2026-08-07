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
    "Headcount of male civil servants working at Senior Civil Service level",
    "Headcount of male civil servants working at Grade 6 or Grade 7 level",
    "Headcount of male civil servants working at Senior or Higher Executive Officer level",
    "Headcount of male civil servants working at Executive Officer level",
    "Headcount of male civil servants working at Administrative Assistant or Administrative Officer level",
    "Headcount of male civil servants with an unreported grade",
    "Total headcount of all male civil servants",
    "Headcount of female civil servants working at Senior Civil Service level",
    "Headcount of female civil servants working at Grade 6 or Grade 7 level",
    "Headcount of female civil servants working at Senior or Higher Executive Officer level",
    "Headcount of female civil servants working at Executive Officer level",
    "Headcount of female civil servants working at Administrative Assistant or Administrative Officer level",
    "Headcount of female civil servants with an unreported grade",
    "Total headcount of all female civil servants",
    "Headcount of civil servants with an unknown sex working at Senior Civil Service level",
    "Headcount of civil servants with an unknown sex working at Grade 6 or Grade 7 level",
    "Headcount of civil servants with an unknown sex working at Senior or Higher Executive Officer level",
    "Headcount of civil servants with an unknown sex working at Executive Officer level",
    "Headcount of civil servants with an unknown sex working at Administrative Assistant or Administrative Officer level",
    "Total headcount of all civil servants with an unreported sex",
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
        logging.FileHandler(_log_dir / "extract_sex_data.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# %%
# Load latest data
source_filepath = f"{SOURCE_DIRECTORY}/{SOURCE_FILE}"

# Initial read as strings
df_sex_str = pd.read_excel(
    source_filepath,
    sheet_name=SHEET_NAME,
    header=None,
    dtype=str,
    engine="odf"
)

# Full read with structural constants
skip_rows = list(range(HEADER_ROW)) + list(range(HEADER_ROW + 1, FIRST_DATA_ROW))
df_sex = pd.read_excel(
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
_sheet_tile = str(df_sex_str.iloc[1, 0]).strip()  # Title is in row 1, not row 0
assert _sheet_tile == EXPECTED_SHEET_TITLE, (
    F"Unexpected title: {_sheet_tile}"
)

# 2: Col headers
_actual_headers = df_sex_str.iloc[HEADER_ROW].tolist()
assert _actual_headers == EXPECTED_COL_NAMES, (
    f"Column headers do not match expected structure. \n"
    f"  Expected: {EXPECTED_COL_NAMES}\n"
    f"  Actual: {_actual_headers}"
)

# %%
# Check for unused N/A values
used_na_vals = {v for v in NA_VALS if (df_sex_str == v).any().any()}
unused_na_vals = [v for v in NA_VALS if v not in used_na_vals]
assert not unused_na_vals, f"Unused NA values (remove from params): {unused_na_vals}"

logger.info("Passed structural and data quality checks")

# %%
# Check for exisitng records in the database

n_existing = pd.read_sql(
    text(
        """select count(*)
        from civil_service.civil_service_statistics_sex cs_sex
        where cs_sex.year = :year"""
    ),
    con=engine,
    params={"year": EXPECTED_YEAR}
).iloc[0, 0]

assert n_existing == 0, (
    f"{EXPECTED_YEAR} already has {n_existing} rows in the CS Stats age table "
    "in the database. Remove before re-running or check if release number is correct"
)

logger.info("Duplicate check passed - no existing rows for %s", EXPECTED_YEAR)

# %%
# Clean and edit data

# Drop "unknown/unreported sex' columns"
df_sex = df_sex.drop(
    columns=[s for s in EXPECTED_COL_NAMES if "unknown sex" in s or "unreported sex" in s]
)
# Edit column names
new_names = [
    "parent_department",
    "organisation_name",
    "Senior Civil Service level - Male",
    "Grades 6 and 7 - Male",
    "Senior and Higher Executive Officers - Male",
    "Executive Officers - Male",
    "Administrative Officers and Assistants - Male",
    "Not reported - Male",
    "All employees - Male",
    "Senior Civil Service level - Female",
    "Grades 6 and 7 - Female",
    "Senior and Higher Executive Officers - Female",
    "Executive Officers - Female",
    "Administrative Officers and Assistants - Female",
    "Not reported - Female",
    "All employees - Female"
]
col_names = dict(zip(df_sex.columns, new_names))
df_sex = df_sex.rename(columns=col_names)
df_sex = df_sex.drop(columns=["parent_department", "All employees - Male", "All employees - Female"])

df_sex = df_sex.melt(
    id_vars=["organisation_name"],
    var_name="sex_and_grade",
    value_name="headcount"
).sort_index(kind="stable").reset_index(drop=True)

# %%

df_sex = df_sex[~df_sex["organisation_name"].str.endswith(" Overall")]

# Delete unwanted strings
delete_str = [
    "(excl. agencies)",
    "(incl. Office of the Advocate General for Scotland)"
    "[Note 20]"
]
for s in delete_str:
    df_sex["organisation_name"] = df_sex["organisation_name"].str.replace(s, "", regex=False)

df_sex["organisation_name"] = df_sex["organisation_name"].str.strip()


df_sex["organisation_name"] = df_sex["organisation_name"].str.replace(
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

df_sex["organisation_name"] = df_sex["organisation_name"].str.replace(ifg_names)

# %%
# Fix row ordering

grade_sex_order = [
    "Senior Civil Service level - Male",
    "Senior Civil Service level - Female",
    "Grades 6 and 7 - Male",
    "Grades 6 and 7 - Female",
    "Senior and Higher Executive Officers - Male",
    "Senior and Higher Executive Officers - Female",
    "Executive Officers - Male",
    "Executive Officers - Female",
    "Administrative Officers and Assistants - Male",
    "Administrative Officers and Assistants - Female",
    "Not reported - Male",
    "Not reported - Female",
]

# dict.fromkeys preserves first-occurrence order and drops duplicates
org_order = list(dict.fromkeys(df_sex["organisation_name"]))

df_sex["organisation_name"] = pd.Categorical(df_sex["organisation_name"], categories=org_order, ordered=True)
df_sex["sex_and_grade"] = pd.Categorical(df_sex["sex_and_grade"], categories=grade_sex_order, ordered=True)
df_sex = df_sex.sort_values(["organisation_name", "sex_and_grade"]).reset_index(drop=True)

# %%
# Add UUID, year and quarter columns
df_sex.insert(0, 'id', [uuid.uuid4() for i in range(len(df_sex))])
df_sex.insert(1, 'year', EXPECTED_YEAR)
df_sex.insert(2, 'quarter', 1)

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

df_sex.insert(
    df_sex.columns.get_loc("organisation_name"),
    "organisation_id",
    resolve_org_id(df_sex, df_orgs, quarter_col="quarter")
)

# %%
# Write to database

df_sex.to_sql(
    name="civil_service_statistics_sex",
    con=engine,
    schema="civil_service",
    if_exists="append",
    index=False,
    chunksize=3000,
    dtype={
        "id": UNIQUEIDENTIFIER,
        "year": SMALLINT,
        "quarter": TINYINT,
        "organisation_id": UNIQUEIDENTIFIER,
        "organisation_name": NVARCHAR(100),
        "sex_and_grade": NVARCHAR(100),
        "headcount": INT
    }
)
