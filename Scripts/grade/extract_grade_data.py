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
