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
HEADER_ROW = 5
FIRST_DATA_ROW = 6
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

# %%
# Load latest data
source = f"{SOURCE_DIRECTORY}/{SOURCE_FILE}"

# Read as strings
df_faith_str = pd.read_excel(
    source,
    sheet_name=SHEET_NAME,
    header=None,
    dtype=str,
    engine="odf"
)

# Full read
_skip_rows = list(range(HEADER_ROW)) + list(range(HEADER_ROW + 1, FIRST_DATA_ROW))
df_faith = pd.read_excel(
    source,
    sheet_name=SHEET_NAME,
    skiprows=_skip_rows,
    na_values=NA_VALS,
    engine="odf"
)

# %%
# perform structural checks

_sheet_title = str(df_faith_str.iloc[1, 0]).strip()
assert _sheet_title == EXPECTED_SHEET_TITLE, (
    f"Unexpected title: {_sheet_title}"
)

_headers = df_faith_str.iloc[HEADER_ROW].tolist()
assert _headers == EXPECTED_COL_NAMES, (
    f"Columns ehaders do not  match expected structure. \n"
    f" Expected: {EXPECTED_COL_NAMES}\n"
    f" Actual: {_headers}"
    )

# %%
# Check n/a values

used_na_vals = {v for v in NA_VALS if (df_faith_str == v).any().any()}
unused_na_vals = [v for v in NA_VALS if v not in used_na_vals]
assert not unused_na_vals, f"Unused N/A values (remove from parameters): {unused_na_vals}"

logger.info("Passe structural and data quality checks")

# %%
# Check whether data exists for this year in the database

n_existing = pd.read_sql(
    text(
        """select count(*)
        from civil_service.civil_service_statistics_faith as cs_faith
        where cs_faith.year = :year"""
    ),
    con=engine,
    params={"year": EXPECTED_YEAR}
).iloc[0, 0]

assert n_existing == 0, (
    f"{EXPECTED_YEAR} already has {n_existing} record in the CS stats faith table. "
    "Remove before re-running or check you're uploading the correct data release"
)
# %%

type(df_faith)

# %%
# clean data

new_names = [
    "parent_department",
    "organisation_name",
    "Christian",
    "Buddhist",
    "Hindu",
    "Jewish",
    "Muslim",
    "Sikh",
    "Any other religion",
    "No religion",
    "Not declared",
    "Not reported",
    "All employees",
    "all_known",
    "percentage"
]
col_names = dict(zip(EXPECTED_COL_NAMES, new_names))
df_faith = df_faith.rename(columns=col_names)
df_faith = df_faith.drop(columns=[
    "parent_department", "all_known", "percentage"
])

# Unpivot data
df_faith = df_faith.melt(
    id_vars=["organisation_name"],
    var_name="religion_or_belief",
    value_name="headcount"
).sort_index(kind="stable").reset_index(drop=True)

# Filter out overall departmental figures
df_faith = df_faith[~df_faith["organisation_name"].str.endswith(" Overall")]

# Delete unwanted strings
delete_str = [
    "(excl. agencies)",
    "(incl. Office of the Advocate General for Scotland)",
    "[Note 20]"
]
for s in delete_str:
    df_faith["organisation_name"] = df_faith["organisation_name"].str.replace(s, "", regex=False)
df_faith["organisation_name"] = df_faith["organisation_name"].str.strip()

df_faith["organisation_name"] = df_faith["organisation_name"].str.replace(
    "Overall Civil Service", "All employees"
)

# %%
# Replace orgs with the in-house IfG names 

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

df_faith["organisation_name"] = df_faith["organisation_name"].str.replace(ifg_names)

# %%
# Fix row ordering

rel_order = [
    "Christian",
    "Buddhist",
    "Hindu",
    "Jewish",
    "Muslim",
    "Sikh",
    "Any other religion",
    "Not declared",
    "Not reported",
    "All employees"
]

org_order = list(dict.fromkeys(df_faith["organisation_name"]))

df_faith["organisation_name"] = pd.Categorical(df_faith["organisation_name"], categories=org_order, ordered=True)
df_faith["reilgion_or_belief"] = pd.Categorical(df_faith["religion_or_belief"], categories=rel_order, ordered=True)
df_faith = df_faith.sort_values(["organisation_name", "religion_or_belief"]).reset_index(drop=True)

# %%
# Add info

df_faith.insert(0, "id", [uuid.uuid4() for x in range(len(df_faith))])
df_faith.insert(1, "year", EXPECTED_YEAR),
df_faith.insert(2, "quarter", 1)

# Match IDs
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

df_faith.insert(
    df_faith.columns.get_loc("organisation_name"),
    "organisation_id",
    resolve_org_id(df_faith, df_orgs, quarter_col="quarter")
)

# %%
# Write to db

df_faith.to_sql(
    name="civil_service_statistics_sexual_orientation",
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
        "religion_or_belief": NVARCHAR(60),
        "headcount": INT
    }
)
