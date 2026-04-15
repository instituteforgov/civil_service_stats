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

import os
import ds_utils.database_operations as dbo
import pandas as pd
import uuid

from sqlalchemy import NVARCHAR, SMALLINT, INT
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER, TINYINT


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
# Read and edit data: drop calculated cols, add UUIDs, normalise col titles to snake_case

df_age = pd.read_excel(FILE_PATH, sheet_name="Data.Collated")

cols = ["Release number",
        "Departmental group",
        "Organisation type",
        "Managed", "Census",
        "Ministerial department/executive agency/selected non-ministerial department",
        "Latest organisation",
        "Latest departmental group"]

df_age.drop(columns=cols)

df_age.insert(0, 'id', [uuid.uuid4() for i in range(len(df_age))])
