# %%
"""
Purpose:
    Import civil service statistics grade data from Excel to SQL server

Input:
    - xlsx: "Grade by department.xlsx"
        - Data.Collated

Output:
    - sql: civil_service.civil_service_statistics_grade
"""

import pandas as pd
import ds_utils.database_operations as dbo
import uuid
import os

from sqlalchemy import NVARCHAR, SMALLINT, INT
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER, TINYINT
from civil_service_stats.utils import resolve_org_id

# %%
FILE_PATH = "C:/Users/" + os.getlogin() + "/INSTITUTE FOR GOVERNMENT/Data - General/Civil service/Civil Service - grade/Grade by department.xlsx"

# %%
# Connect to d/b

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

df_grade = pd.read_excel(FILE_PATH, sheet_name="Data.Collated")

# %%
# Edit data

# Drop calculated columns
df_grade = df_grade.drop(columns=[
    "Release number",
    "Departmental group",
    "Organisation type",
    "Managed",
    "Census",
    "Ministerial department/executive agency/selected non-ministerial department",
    "Latest organisation",
    "Latest departmental group"
])

# Add ID column
df_grade.insert(0, 'id', [uuid.uuid4() for i in range(len(df_grade))])

# Edit column names
df_grade.columns = df_grade.columns.str.strip().str.lower()
df_grade = df_grade.rename(columns={"organisation": "organisation_name", "fte": "headcount_fte"})
df_grade["organisation_name"] = df_grade["organisation_name"].str.replace(r"\s*-\s*\d{4}\s*iteration\s*", "", regex=True)

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

df_grade.insert(
    df_grade.columns.get_loc("organisation_name"),
    "organisation_id",
    resolve_org_id(df_grade, df_orgs, quarter_col="quarter")
)

# %%
# Write to database

df_grade.to_sql(
    name="civil_service_statistics_grade",
    con=engine,
    schema="civil_service",
    if_exists="replace",
    index=False,
    chunksize=3000,
    dtype={
        "id": UNIQUEIDENTIFIER,
        "quarter": TINYINT,
        "organisation_id": UNIQUEIDENTIFIER,
        "year": SMALLINT,
        "organisation_name": NVARCHAR(100),
        "age": NVARCHAR(20),
        "headcount_fte": INT
    }
)
