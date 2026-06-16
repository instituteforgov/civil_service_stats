# %%

import pandas as pd
import ds_utils.database_operations as dbo
import uuid
import os

from sqlalchemy import NVARCHAR, SMALLINT, INT
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER, TINYINT
from civil_service_stats.utils import resolve_org_id

# %%
# Set constants

FILE_PATH = "C:/Users/" + os.getlogin() + "/INSTITUTE FOR GOVERNMENT/Data - General/Civil service/Civil service - professions and functions/Professions and functions of civil servants - with assumed DWP professions averages.xlsx"
SHEET_NAME = "Data.Collated_FunctionbyDept"

# %%
# Connect to D/B

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
# Read data

df_funcs = pd.read_excel(FILE_PATH, sheet_name=SHEET_NAME)

# %%

