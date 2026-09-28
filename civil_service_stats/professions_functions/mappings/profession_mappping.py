# %%
import os
import uuid

import pandas as pd

import ds_utils.database_operations as dbo
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy import NVARCHAR

from civil_service_stats.utils import make_series_sentence_case

# %%
FILE_PATH = "C:/Users/" + os.getlogin() + "/INSTITUTE FOR GOVERNMENT/Data - General/Civil service/Civil service - professions and functions/Professions and functions of civil servants - with assumed DWP professions averages.xlsx"
SHEET_NAME = "Ref_Profession classification"

PRESERVE_CAPITALISATION_GROUPS = [
    "Government Digital and Data"
]

# %%
df_mapping = pd.read_excel(
    FILE_PATH,
    sheet_name=SHEET_NAME,
    usecols="A:D"
)

# %%
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
df_mapping.columns = df_mapping.columns.str.replace("(IfG)", "").str.lower().str.strip().str.replace(" ", "_")

df_mapping["profession_group"] = make_series_sentence_case(df_mapping["profession_group"], PRESERVE_CAPITALISATION_GROUPS)

df_mapping.insert(0, 'id', [uuid.uuid4() for k in range(len(df_mapping))])

# %%
df_mapping.to_sql(
    name="professions_mapping",
    con=engine,
    schema="civil_service",
    if_exists="replace",
    index=False,
    dtype={
        "id": UNIQUEIDENTIFIER,
        "profession_name": NVARCHAR(50),
        "profession_group": NVARCHAR(50),
        "profession_category": NVARCHAR(40),
        "government_classification": NVARCHAR(40)
    }
)

# %%
