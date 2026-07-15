# %%

import ds_utils.database_operations as dbo
import pandas as pd
import uuid
import os

from sqlalchemy import NVARCHAR, SMALLINT, INT
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER, TINYINT
from civil_service_stats.utils import resolve_org_id

# %%
FILE_PATH = "C:/Users/" + os.getlogin() + "/INSTITUTE FOR GOVERNMENT/Data - General/Civil service/Civil Service - diversity/Civil Service - sex/Sex of civil servants.xlsx"
SHEET_NAME = "Data.Collated"

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

df_sex = pd.read_excel(FILE_PATH, sheet_name=SHEET_NAME)

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

df_sex = df_sex.drop(columns=cols)

df_sex.insert(0, 'id', [uuid.uuid4() for i in range(len(df_sex))])

df_sex.columns = df_sex.columns.str.strip().str.lower().str.replace(r"\s+", "_", regex=True)

df_sex = df_sex.rename(columns={"organisation": "organisation_name"})

df_sex["organisation_name"] = df_sex["organisation_name"].str.replace(r"\s*-\s*\d{4}\s*iteration\s*", "", regex=True)

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

df_sex.insert(
    df_sex.columns.get_loc("organisation_name"),
    "organisation_id",
    resolve_org_id(df_sex, df_orgs, quarter_col="quarter")
)

# %%
# Write to d/b

df_sex.to_sql(
    name="civil_service_statistics_sex",
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
        "sex_and_grade": NVARCHAR(50),
        "headcount": INT
    }
)

# %%
