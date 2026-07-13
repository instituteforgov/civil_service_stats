# %%

import pandas as pd
import os
import ds_utils.database_operations as dbo

from cs_data_utils.utils import compare_dataframes
from civil_service_stats.utils import add_iteration_suffix

# %%
# Set filepaths
EXCEL_PATH = "C:/Users/" + os.getlogin() + "/INSTITUTE FOR GOVERNMENT/Data - General/Civil service/Civil service - pay/Pay working file.xlsx"
SHEET_NAME = "Collated.Organisation x grade"
SQL_PATH = "C:/Users/" + os.getlogin() + "/INSTITUTE FOR GOVERNMENT/Data - General/Civil service/Civil Service Statistics/Scripts/civil_service_stats/pay/legacy/compare_pay_organisations_data"


# %%
# Connect to DB

engine = engine = engine = dbo.connect_sql_db(
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
# Read in SQL and Excel data

df_excel = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME)

with open(SQL_PATH, encoding="utf-8") as f:
    sql = f.read()
df_sql = pd.read_sql(sql, con=engine)

# %%
# Edit data

df_excel = df_excel.drop(columns=[
    "Managed", "Census", "Ministerial department/executive agency/selected non-ministerial department"
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
# Compare dataframes

key_cols = ["Year", "Quarter", "Organisation", "Grade", "Median salary"]

compare_dataframes(df_excel, df_sql, key_cols)
