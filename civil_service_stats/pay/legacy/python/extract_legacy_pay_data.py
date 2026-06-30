# %%

import pandas as pd
import ds_utils.database_operations as dbo
import uuid
import os

from sqlalchemy import NVARCHAR, SMALLINT, INT
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER, TINYINT
from civil_service_stats.utils import resolve_org_id

# %%
# Set file path constant

FILE_PATH = "C:/Users/" + os.getlogin() + "/INSTITUTE FOR GOVERNMENT/Data - General/Civil service/Civil Service - pay/Pay working file.xlsx"

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

df_pay = pd.read_excel(FILE_PATH, sheet_name="Collated.Organisation x grade")

# %%
# Edit data

# Drop columns
df_pay = df_pay.drop(columns=[
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
df_pay.insert(0, "id", [uuid.uuid4() for _ in range(len(df_pay))])

# Edit column names and remove iteration suffixes
df_pay.columns = df_pay.columns.str.strip().str.lower().str.replace(" ", "_")
df_pay = df_pay.rename(columns={"organisation": "organisation_name"})
df_pay["organisation_name"] = df_pay["organisation_name"].str.replace(r"\s*-\s*\d{4}\s*iteration\s*", "", regex=True)

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

df_pay.insert(
    df_pay.columns.get_loc("organisation_name"),
    "organisation_id",
    resolve_org_id(df_pay, df_orgs, quarter_col="quarter")
)

# %%
df_pay

# %%
# Write to DB

df_pay.to_sql(
    name="civil_service_statistics_pay",
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
        "grade": NVARCHAR(50),
        "median_salary": INT,
    }
)
