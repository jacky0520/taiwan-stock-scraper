"""Helpers for cleaning TWSE data."""

import numpy as np
import pandas as pd


def roc_to_date(roc_date):
    """
    Convert a Republic of China (Minguo) calendar date such as '113/09/02'
    to a pandas Timestamp (2024-09-02). ROC year + 1911 = Gregorian year.
    """
    year, month, day = (int(part) for part in str(roc_date).strip().split("/"))
    return pd.Timestamp(year + 1911, month, day)


def to_number(series):
    """
    Turn TWSE text values into floats: remove thousands separators and the
    'X' marker TWSE puts in front of price changes on ex-dividend days;
    placeholders such as '--' become NaN.
    """
    cleaned = (series.astype(str)
                     .str.replace(",", "", regex=False)
                     .str.replace("X", "", regex=False)
                     .str.strip())
    cleaned = cleaned.replace({"": np.nan, "--": np.nan, "---": np.nan})
    return pd.to_numeric(cleaned, errors="coerce")


def month_starts(start, end):
    """
    All first-of-month dates from `start` to `end` inclusive, as 'YYYYMMDD'
    strings. `start` and `end` are 'YYYY-MM' strings.
    """
    months = pd.period_range(start=start, end=end, freq="M")
    return [p.start_time.strftime("%Y%m%d") for p in months]
