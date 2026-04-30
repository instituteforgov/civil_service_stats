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

