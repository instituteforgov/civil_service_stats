# %%
"""
    Purpose:
        Compare the output of compare_age_organisations_data.sql with 'Data.Collated' sheet in "Age by Department.xlsx" to check they match

    Inputs:
        - xlsx: "Age by Department.xlsx"
        - sql: "compare_age_organisations_data.sql"

    Outputs:
        - Comparison summary
"""

import os

import ds_utils.database_operations as dbo
import pandas as pd
from utils import add_iteration_suffix

# %%

EXCEL_PATH = "C:/Users/" + os.getlogin() + "/INSTITUTE FOR GOVERNMENT/Data - General/Civil service/Civil Service - diversity/Civil Service - Age/Age by Department.xlsx"
SQL_PATH = "C:/Users/" + os.getlogin() + "/INSTITUTE FOR GOVERNMENT/Data - General/Civil service/Civil Service Statistics/Scripts/age/sql/compare_age_organisations_data.sql"

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

df_excel = pd.read_excel(EXCEL_PATH, sheet_name="Data.Collated")

with open(SQL_PATH, encoding="utf-8") as f:
    sql = f.read()

df_sql = pd.read_sql(sql, con=engine)

# %%

df_excel.columns

# %%
# Edit data

df_excel = df_excel.drop(columns=[
    "Managed",
    "Census",
    "Ministerial department/executive agency/selected non-ministerial department"
])

df_sql["Organisation"] = df_sql.apply(add_iteration_suffix, col="Organisation", axis=1)
