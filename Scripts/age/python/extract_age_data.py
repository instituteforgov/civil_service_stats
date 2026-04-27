# %%
"""
Purpose
    Import Civil Service Statistics age data from Excel to SQL server

Input
    - xlsx: "Age by Department.xlsx"
        - Data.Collated

Output
    - sql: civil_service.civil_service_statistics_age
"""
import ds_utils.database_operations as dbo
import pandas as pd
import uuid
import os

from sqlalchemy import NVARCHAR, SMALLINT, INT
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER, TINYINT
from Scripts.utils import resolve_org_id

# %%
FILE_PATH = "C:/Users/" + os.getlogin() + "/INSTITUTE FOR GOVERNMENT/Data - General/Civil service/Civil Service - diversity/Civil Service - age/Age by Department.xlsx"

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
# Read in data

df_age = pd.read_excel(FILE_PATH, sheet_name="Data.Collated")

# %%
# Edit data

cols = ["Release number",
        "Departmental group",
        "Organisation type",
        "Managed",
        "Census",
        "Ministerial department/executive agency/selected non-ministerial department",
        "Latest organisation",
        "Latest departmental group"]

df_age = df_age.drop(columns=cols)

df_age.insert(0, 'id', [uuid.uuid4() for i in range(len(df_age))])

df_age.columns = df_age.columns.str.strip().str.lower().str.replace(r"\s+", "_", regex=True)

df_age = df_age.rename(columns={"organisation": "organisation_name"})

df_age["organisation_name"] = df_age["organisation_name"].str.replace(r"\s*-\s*\d{4}\s*iteration\s*", "", regex=True)

# %%
# Insert ids for orgs from d/b
# Match organisation names and quarter/year pairs with civil_service.organisation

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

df_age.insert(
    df_age.columns.get_loc("organisation_name"),
    "organisation_id",
    resolve_org_id(df_age, df_orgs, quarter_col="quarter")
)

# %%
# Write to d/b

df_age.to_sql(
    name="civil_service_statistics_age",
    con=engine,
    schema="civil_service",
    if_exists="replace",
    index=False,
    chunksize=3000,
    dtype={
        "id": UNIQUEIDENTIFIER,
        "quarter": TINYINT,
        "year": SMALLINT,
        "organisation": NVARCHAR(100),
        "age": NVARCHAR(20),
        "headcount": INT
    }
)
