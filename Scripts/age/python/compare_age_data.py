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
# Edit data

# Drop columns we don't use
df_excel = df_excel.drop(columns=[
    "Managed",
    "Census",
    "Ministerial department/executive agency/selected non-ministerial department"
])

# Add YYYY iteration suffixes to Organisation column
df_sql["Organisation"] = df_sql.apply(add_iteration_suffix, col="Organisation", axis=1)

# Add YYYY iteration suffixes to Latest organisation column
iteration_suffixes = {
    "Department for Culture, Media and Sport": "Department for Culture, Media and Sport - 2023 iteration",
    "Ministry of Housing, Communities & Local Government": "Ministry of Housing, Communities & Local Government - 2024 iteration",
}

df_sql["Latest organisation"] = df_sql["Latest organisation"].map(lambda x: iteration_suffixes.get(x, x))

# %%
# Check columns match

columns_excel_only = [col for col in df_excel.columns if col not in df_sql.columns]
columns_sql_only = [col for col in df_sql.columns if col  not in df_excel.columns]
columns_both = [col for col in df_excel.columns if col in df_sql.columns]

print(f"Columns in Excel frame only: {columns_excel_only}")
print(f"Columns in SQL frame only: {columns_sql_only}")
print(f"Columns in both: {columns_both}")

# %%
# Check number of rows match

assert len(df_sql) == len(df_excel), ("Row counts in SQL and Excel frames don't match!")

# %%
# Compare key values - those values which uniquely identify rows 

keys = [
   "Quarter", "Year", "Headcount", "Age", "Organisation"
]

df_merged = df_sql.merge(df_excel, on=keys, how='outer', suffixes=("_sql", "_excel"), indicator=True)

rows_excel_only = df_merged[df_merged["_merge"] == "right_only"]
rows_sql_only = df_merged[df_merged["_merge"] == "left_only"]
rows_both = df_merged[df_merged["_merge"] == "both"]

print(f"Rows in Excel frame only: {rows_excel_only}")
print(f"Rows in SQL frame only: {rows_sql_only}")
print(f"Rows in both: {rows_both}")

assert len(df_sql) == len(df_merged), f"Row counts in SQL/Excel and merged frames don't match!"

# %%
# Compare values in the matched rows (i.e. check that, for example, the same organisations are appearing where they should be)

values = [col for col in columns_both if col not in keys] 

for col in values:
    sql_col = f"{col}_sql"
    excel_col = f"{col}_excel"

    if sql_col in rows_both and excel_col in rows_both:
        sql_series = rows_both[sql_col]
        excel_series = rows_both[excel_col]
        mask = (
            (sql_series == excel_series) 
            | (rows_both[sql_col].isna() & rows_both[excel_col].isna())
        )



# %%
