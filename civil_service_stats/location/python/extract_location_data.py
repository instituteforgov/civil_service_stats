# %%
"""
Purpose:
    Extract Civil Service Statistics location data and write to database

Input:
    - xlsx: "Location working file.xlsx"
        - Sheet name = Data.Collated

Output:
    - sql: civil_service.civil_service_statistics_location
"""

import pandas as pd
import ds_utils.database_operations as dbo
import uuid
import os

from sqlalchemy import NVARCHAR, SMALLINT, INT
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER, TINYINT
from civil_service_stats.utils import resolve_org_id

# %%
# Set file path constant

FILE_PATH = "C:/Users/" + os.getlogin() + "/INSTITUTE FOR GOVERNMENT/Data - General/Civil service/Civil Service - location/Location working file.xlsx"

# %%
# Establish d/b connection

engine = engine = dbo.connect_sql_db(
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
# Load data

df_location = pd.read_excel(FILE_PATH, sheet_name="Collated.Org x region")

# %%
# Edit data

# Drop calculated cols
df_location = df_location.drop(columns=[
    "Managed?",
    "Release number",
    "Departmental group",
    "Organisation type",
    "Managed",
    "Census",
    "Ministerial department/executive agency/selected non-ministerial department",
    "Latest organisation",
    "Latest departmental group"
])

# Add UUID column
df_location.insert(0, 'id', [uuid.uuid4() for i in range(len(df_location))])

# Edit col names
df_location.columns = df_location.columns.str.strip().str.lower()
df_location = df_location.rename(columns={"organisation": "organisation_name"})
df_location["organisation_name"] = df_location["organisation_name"].str.replace(
    r"\s*-\s*\d{4}\s*iteration\s*", "", regex=True)

# %%
# Insert organisation IDs from canonical orgs database

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

df_location.insert(
    df_location.columns.get_loc("organisation_name"),
    "organisation_id",
    resolve_org_id(df_location, df_orgs, quarter_col="quarter")
)

# %%
# Write to d/b

df_location.to_sql(
    name="civil_service_statistics_location",
    con=engine,
    schema="civil_service",
    if_exists="replace",
    index=False,
    chunksize=3000,
    dtype={
        "id": UNIQUEIDENTIFIER,
        "organisation_id": UNIQUEIDENTIFIER,
        "organisation_name": NVARCHAR(100),
        "year": SMALLINT,
        "quarter": TINYINT,
        "region": NVARCHAR(30),
        "total": INT
    }
)
