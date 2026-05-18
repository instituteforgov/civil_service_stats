# %%
"""
Purpose:
    Extract Civil Service Statistics location data and write to database

Input:
    - xlsx: "Location working file.xlsx"
        - Sheet name = Data.Collated

Output:
    - sql: civil_service.civil_service_statistics_location
"""

import pandas as pd
import ds_utils.database_operations as dbo
import uuid
import os

from sqlalchemy import NVARCHAR, SMALLINT, INT
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER, TINYINT
from civil_service_stats.utils import resolve_org_id

# %%
# Set file path constant

FILE_PATH = "C:/User" + os.getlogin() + "INSTITUTE FOR GOVERNMENT/Data - General/Civil service/Civil Service - location/Location working file.xlsx"

# %%
# Establish d/b connection

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
