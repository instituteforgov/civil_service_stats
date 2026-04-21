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
