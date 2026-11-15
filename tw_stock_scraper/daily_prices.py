"""
Daily trading data (open, high, low, close, volume, ...) for one stock,
from TWSE (listed) or TPEx (OTC). One request covers one month.
"""

from pathlib import Path

import pandas as pd

from .client import Client
from .markets import MARKETS
from .utils import month_starts, roc_to_date, to_number

COLUMNS = ["date", "volume_shares", "value_twd", "open", "high", "low",
           "close", "change", "transactions"]


def _column_for(field):
    """English column for an exchange field name, and the unit multiplier."""
    f = field.replace(" ", "").replace("　", "")
    if "日" in f and "期" in f:
        return "date", 1
    if "筆數" in f:
        return "transactions", 1
    if "成交" in f and ("股" in f or "張" in f):
        # TWSE reports shares; TPEx reports thousands of shares (仟股) or
        # lots of 1,000 shares (張). Convert all to shares.
        return "volume_shares", 1000 if ("仟" in f or "張" in f) else 1
    if "成交" in f and ("金額" in f or "元" in f):
        return "value_twd", 1000 if "仟" in f else 1
    for keyword, col in [("開盤", "open"), ("最高", "high"), ("最低", "low"),
                         ("收盤", "close"), ("漲跌", "change")]:
        if keyword in f:
            return col, 1
    return None, 1


def parse_month(fields, rows):
    """Turn one month of raw rows into a clean DataFrame with English columns."""
    raw = pd.DataFrame(rows, columns=fields)
    df = pd.DataFrame(index=raw.index)
    for field in fields:
        col, scale = _column_for(field)
        if col is None or col in df.columns:
            continue
        if col == "date":
            df["date"] = raw[field].map(roc_to_date)
        else:
            df[col] = to_number(raw[field]) * scale
    return df.reindex(columns=COLUMNS)


def _try_markets(stock_id, month_start, client):
    """Find the market that has data for this stock: (name, table) or (None, None)."""
    for name, market in MARKETS.items():
        table = market.daily_month(client, stock_id, month_start)
        if table is not None:
            return name, table
    return None, None


def fetch_range(stock_id, start, end, market="auto", client=None):
    """
    Daily data from month `start` to month `end` ('YYYY-MM').
    market: 'twse', 'tpex', or 'auto' (try TWSE first, then TPEx).
    """
    client = client or Client()
    frames = []
    for month in month_starts(start, end):
        label = f"{month[:4]}-{month[4:6]}"
        if market == "auto":
            print(f"{stock_id}: fetching {label}, checking TWSE then TPEx ...")
            found, table = _try_markets(stock_id, month, client)
            if found is not None:
                market = found                 # use this market from now on
                print(f"  {stock_id} is traded on {market.upper()}")
        else:
            print(f"{stock_id}: fetching {label} from {market.upper()} ...")
            table = MARKETS[market].daily_month(client, stock_id, month)
        if table is None:
            print("  no data")
            continue
        frames.append(parse_month(*table))

    if not frames:
        return pd.DataFrame(columns=COLUMNS)
    return (pd.concat(frames, ignore_index=True)
              .drop_duplicates(subset="date")
              .sort_values("date", ignore_index=True))


def update_csv(stock_id, start, end, market="auto", data_dir="data", client=None):
    """
    Fetch data and merge it into data/<stock_id>_daily.csv. Rows are matched
    by date: new days are added and existing days are refreshed.
    """
    path = Path(data_dir) / f"{stock_id}_daily.csv"
    path.parent.mkdir(parents=True, exist_ok=True)

    new = fetch_range(stock_id, start, end, market, client)
    if path.exists():
        old = pd.read_csv(path, parse_dates=["date"])
        combined = pd.concat([old, new], ignore_index=True)
    else:
        combined = new

    combined = (combined.drop_duplicates(subset="date", keep="last")
                        .sort_values("date", ignore_index=True))
    combined.to_csv(path, index=False)
    print(f"Saved {len(combined)} trading days to {path}")
    return combined
