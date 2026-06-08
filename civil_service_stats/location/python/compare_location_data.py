# %%

import os
import ds_utils.database_operations as dbo
import pandas as pd
from civil_service_stats.utils import add_iteration_suffix
# from IPython.display import display

# %%
# Set file paths, connect to d/b an load data

EXCEL_PATH = "C:/Users/" + os.getlogin() + "/INSTITUTE FOR GOVERNMENT/Data - General/Civil service/Civil Service - location/Location working file.xlsx"
SHEET_NAME = "Collated.Org x region"

SQL_PATH = "C:/Users/" + os.getlogin() + "/INSTITUTE FOR GOVERNMENT/Data - General/Civil Service/Civil Service Statistics/Scripts/civil_service_stats/location/sql/compare_location_organisations_data"

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


df_excel = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME)

with open(SQL_PATH, encoding="utf-8") as f:
    sql = f.read()
df_sql = pd.read_sql(sql, con=engine)

# %%
# Edit data

df_excel = df_excel.drop(columns=[
    "Managed", "Managed?", "Census", "Ministerial department/executive agency/selected non-ministerial department"
])

df_sql["Organisation"] = df_sql.apply(add_iteration_suffix, col="Organisation", axis=1)

# Manually add YYYY suffixes to latest orgs where relevant
suffixes = {
    "Department for Culture, Media and Sport": "Department for Culture, Media and Sport - 2023 iteration",
    "Ministry of Housing, Communities & Local Government": "Ministry of Housing, Communities & Local Government - 2024 iteration",
}

df_sql["Latest organisation"] = df_sql["Latest organisation"].map(lambda x: suffixes.get(x, x))

# Set latest organisation to 'Organisation' where it is currently non-civil service
df_sql["Latest organisation"] = df_sql.apply(
        lambda row: row["Organisation"] if row["Latest organisation"] == "Non-civil service" else row["Latest organisation"],
        axis=1,
)

# %%
# Compare columns

excel_only = [col for col in df_excel.columns if col not in df_sql.columns]
sql_only = [col for col in df_sql.columns if col not in df_excel.columns]
cols_both = [col for col in df_excel.columns if col in df_sql.columns]

print(f"Columns in Excel frame only: {excel_only}")
print(f"Columns in SQL frame only: {sql_only}")
print(f"Columns in both frames: {cols_both}")

# %%

assert len(df_sql) == len(df_excel), f"Row count mismatch: SQL Dataframe has {len(df_sql)} rows, Excel DataFrame has {len(df_excel)}"

# %%
