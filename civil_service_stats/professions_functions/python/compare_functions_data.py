
import pandas as pd
import os
import ds_utils.database_operations as dbo
from IPython.display import display

from civil_service_stats.utils import add_iteration_suffix

# %%
# Set filepaths
EXCEL_PATH = "C:/Users/" + os.getlogin() + "/INSTITUTE FOR GOVERNMENT/Data - General/Civil service/Civil service - professions and functions/Professions and functions of civil servants - with assumed DWP professions averages.xlsx"
SHEET_NAME = "Data.Collated_FunctionbyDept"
SQL_PATH = "C:/Users/" + os.getlogin() + "/INSTITUTE FOR GOVERNMENT/Data - General/Civil service/Civil Service Statistics/Scripts/civil_service_stats/professions_functions/sql/compare_profs_organisations_data"

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
# Compare key column values

key_cols = ["Year", "Quarter", "Organisation", "Function", "FTE", "Function group"]

df_merge = df_sql.merge(
    df_excel, on=key_cols, how='outer', suffixes=("_sql", "_excel"), indicator=True
    )

rows_excel = df_merge[df_merge["_merge"] == "right_only"]
rows_sql = df_merge[df_merge["_merge"] == "left_only"]
rows_both = df_merge[df_merge["merge"] == "both"]

print(f"Rows in SQL frame only: {len(rows_sql)}")
print(f"Rows in Excel frame only: {len(rows_excel)}")
print(f"Rows in both: {len(rows_both)}")

assert len(df_merge) == len(df_sql), f"Merged frame has {len(df_merge)} rows but SQL/Excel frames have {len(df_sql)} rows!"

# %%
# Compare values in calculated columns

cols = [col for col in cols_both if col not in key_cols]

mismatch_mask = {}
for col in cols:
    sql_col = f"{col}_sql"
    excel_col = f"{col}_excel"

    if sql_col in rows_both and excel_col in rows_both:
        sql_series = rows_both[sql_col]
        excel_series = rows_both[excel_col]
        match_mask = (
            (sql_series == excel_series) |
            (rows_both[sql_col].isna() & rows_both[excel_col].isna())
            )
    if (~match_mask).any():
        mismatch_mask[col] = (~match_mask)

if mismatch_mask:
    display({col: int(mask.sum()) for col, mask in mismatch_mask.items()})
    for col, mask in mismatch_mask.items():
        sql_col = f"{col}_sql"
        excel_col = f"{col}_excel"
        preview = (
            rows_both.loc[mask, ["Year", "Organisation", sql_col, excel_col]]
            .drop_duplicates()
            .reset_index(drop=True)
        )
        print(f"Mismatches in '{col}':")
        display(preview)
else:
    print("No value mismatches in matched rows")