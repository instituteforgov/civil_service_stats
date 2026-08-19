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

FILE_PATH = "C:/Users/" + os.getlogin() + "/INSTITUTE FOR GOVERNMENT/Data - General/Civil service/Civil service - leaving cause/NEW Leaving Cause.xlsx"
SHEET_NAME = "Collated.LeavingCause"

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

df_causes = pd.read_excel(FILE_PATH, sheet_name=SHEET_NAME)

# %%
# Edit data

# Drop calculated columns
df_causes = df_causes.drop(columns=[
    "Release number",
    "Departmental group",
    "Organisation type",
    "Managed",
    "Census",
    "Ministerial department/executive agency/selected non-ministerial department",
    "Ministerial department?",
    "Latest organisation",
    "Latest departmental group"
])

# Add ID col
df_causes.insert(0, "id", [uuid.uuid4() for _ in range(len(df_causes))])

# Edit column names
df_causes.columns = df_causes.columns.str.strip().str.lower().str.replace(" ", "_")
df_causes = df_causes.rename(columns={"organisation": "organisation_name", "fte": "headcount_fte"})
df_causes["organisation_name"] = df_causes["organisation_name"].str.replace(r"\s*-\s*\d{4}\s*iteration\s*", "", regex=True)

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

df_causes.insert(
    df_causes.columns.get_loc("organisation_name"),
    "organisation_id",
    resolve_org_id(df_causes, df_orgs, quarter_col="quarter")
)
# %%

df_causes.to_sql(
    name="civil_service_statistics_leaving_cause",
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
        "leaving_cause": NVARCHAR(100),
        "headcount": INT,
    }
)
