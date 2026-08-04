# %%
import pandas as pd

# %%


def resolve_org_id(
    df: pd.DataFrame,
    df_org_id: pd.DataFrame,
    org_col: str = "organisation_name",
    year_col: str = "year",
    quarter_col: str | int = "quarter",
) -> pd.Series:
    """Return a Series of organisation UUIDs matched by name and year/quarter.

    Args:
        df: Source DataFrame containing the rows to resolve.
        df_org_id: Reference DataFrame with columns id, name, start_year,
            start_quarter, end_year, end_quarter.
        org_col: Column in df containing the organisation name.
        year_col: Column in df containing the survey year.
        quarter_col: Column in df containing the survey quarter, or a scalar
            integer to apply the same quarter to all rows.

    Returns:
        Series indexed like df, with the resolved UUID where a unique active
        organisation record was found, and NaN where unresolvable.
    """
    lookup = df[[org_col, year_col]].rename(columns={org_col: "name", year_col: "year"})
    if isinstance(quarter_col, str):
        lookup["quarter"] = df[quarter_col]
    else:
        lookup["quarter"] = quarter_col
    merged = (
        lookup
        .rename_axis("_orig_idx")
        .reset_index()
        .merge(
            df_org_id[["id", "name", "start_year", "start_quarter", "end_year", "end_quarter"]],
            on="name",
            how="left",
        )
    )
    active = (
        (merged["start_year"].isna() |
         (merged["start_year"] < merged["year"]) |
         ((merged["start_year"] == merged["year"]) & (merged["start_quarter"] <= merged["quarter"])))
        &
        (merged["end_year"].isna() |
         (merged["end_year"] > merged["year"]) |
         ((merged["end_year"] == merged["year"]) & (merged["end_quarter"] >= merged["quarter"])))
    )
    merged = merged[active]
    counts = merged.groupby("_orig_idx")["id"].count()
    unique_idx = counts[counts == 1].index
    result = merged[merged["_orig_idx"].isin(unique_idx)].set_index("_orig_idx")["id"]
    return result.reindex(df.index)

# %%


def add_iteration_suffix(row: pd.Series, col: str) -> str:
    """
    Add ' - YYYY iteration' to "Organisation" values where appropriate, i.e. to
    differentiate between the two versions of DCMS and MHCLG which have each
    existed, then gone out of existence, then come back into existence in their history

    Parameters:
        row (pd.Series): A row of the DataFrame containing the specified column and a year column
        col (str): The specified column to search for organisation names

    Returns:
        str: The modified "Organisation" with relevant iteration suffix (if applicable), else the orginal value
    """
    if row[col] == "Department for Culture, Media and Sport":
        if row["Year"] <= 2017:
            return "Department for Culture, Media and Sport - 2017 iteration"
        elif row["Year"] >= 2023:
            return "Department for Culture, Media and Sport - 2023 iteration"
        else:
            return row[col]
    elif row[col] == "Ministry of Housing, Communities & Local Government":
        if row["Year"] <= 2021 and row["Year"] >= 2018:
            return "Ministry of Housing, Communities & Local Government - 2018 iteration"
        elif row["Year"] >= 2024:
            return "Ministry of Housing, Communities & Local Government - 2024 iteration"
        else:
            return row[col]
    else:
        return row[col]

# %%


def find_and_replace(
    df: pd.DataFrame,
    col: str = "organisation_name") -> None:
    """
    Find and replace organisation names so that they match the names
    we have on record in the database. E.g., Medicines and Healthcare Products Regulatory Agency
    is stored in the research database as Medicines and Healthcare products Regulatory Agency
    """
    ifg_names = {
        "Advisory, Concilliation and Arbitration Service": "Advisory Concilliation and Arbitration Service",
        "Wilton Park": "Wilton Park Executive agency",
        "Medicines and Healthcare Products Regulatory Agency": "Medicines and Healthcare products Regulatory Agency",
        "Ministry of Housing, Communities and Local Government": "Ministry of Housing, Communities & Local Government",
        "Office for Standards in Education, Children's Services and Skills": "Office for Standards in Education, Children’s Services and Skills",
        "Crown Office and Procurator Fiscal Service": "Crown Office and Procurator Fiscal",
        "UK Export Finance": "Export Credits Guarantee Department",
        "Water Services Regulation Authority": "Ofwat"
    }

    df[col] = df[col].replace(ifg_names)
