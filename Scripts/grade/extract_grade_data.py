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
from sqlalchemy.dialects import UNIQUEIDENTIFIER, TINYINT
from utils import resolve_org_id

# %%
FILE_PATH = "C:/Users/" + os.getlogin() + "/INSTITUTE FOR GOVERNMENT/Data - General/Civil service/Civil Service - grade/Grade by departmentCivil Service Age Working File.xlsx"

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

