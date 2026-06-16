# %%

import pandas as pd
import ds_utils.database_operations as dbo
import uuid
import os

from sqlalchemy import NVARCHAR, SMALLINT, INT
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER, TINYINT
from civil_service_stats.utils import resolve_org_id

# %%
# Set constants

FILE_PATH = "C:/Users/" + os.getlogin() + "/INSTITUTE FOR GOVERNMENT/Data - General/Civil service/Civil service - professions and functions/Professions and functions of civil servants - with assumed DWP professions averages.xlsx"
SHEET_NAME = "Data.Collated_FunctionbyDept"

# %%
# Connect to D/B

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
# Read data

df_funcs = pd.read_excel(FILE_PATH, sheet_name=SHEET_NAME)

# %%
# Edit data

# Drop calculated columns
df_funcs = df_funcs.drop(columns=[
    "Release number",
    "Departmental group",
    "Organisation type",
    "Managed",
    "Census",
    "Ministerial department/executive agency/selected non-ministerial department",
    "Latest organisation",
    "Latest departmental group"
])

# Add ID col
df_funcs.insert(0, "id", [uuid.uuid4() for _ in range(len(df_funcs))])

# Edit column names
df_funcs.columns = df_funcs.columns.str.strip().str.lower().str.replace(" ", "_")
df_funcs = df_funcs.rename(columns={"organisation": "organisation_name", "fte": "headcount_fte"})
df_funcs["organisation_name"] = df_funcs["organisation_name"].str.replace(r"\s*-\s*\d{4}\s*iteration\s*", "", regex=True)

# %%
# Add org ID column

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

df_funcs.insert(
    df_funcs.columns.get_loc("organisation_name"),
    "organisation_id",
    resolve_org_id(df_funcs, df_orgs, quarter_col="quarter")
)

# %%
# Write to DB

df_funcs.to_sql(
    name="civil_service_statistics_functions",
    con=engine,
    schema="civil_service",
    if_exists="replace",
    index=False,
    chunksize=3000,
    dtype={
        "id": UNIQUEIDENTIFIER,
        "year": SMALLINT,
        "quarter": TINYINT,
        "organisation_id": UNIQUEIDENTIFIER,
        "organisation_name": NVARCHAR(100),
        "function": NVARCHAR(20),
        "headcount_fte": INT,
        "function_group": NVARCHAR(50),
    }
)
