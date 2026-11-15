"""
Valuation ratios (dividend yield, P/E, P/B) of all stocks on a given day,
from TWSE (listed) and TPEx (OTC).
"""

from pathlib import Path

import pandas as pd

from .client import Client
from .markets import MARKETS
from .utils import to_number

# Exchange field names differ slightly between markets and over time, so
# columns are matched by a keyword (Traditional Chinese, as sent).
FIELD_KEYWORDS = [
    ("代號", "code"),                  # stock code
    ("名稱", "name"),                  # stock name
    ("收盤", "close"),                 # closing price (TWSE only)
    ("殖利率", "dividend_yield_pct"),
    ("每股股利", "dividend_per_share"),  # TPEx only
    ("股利年度", "dividend_year"),
    ("本益比", "pe_ratio"),
    ("淨值比", "pb_ratio"),
    ("財報", "report_period"),          # TWSE only
]
NUMERIC = ["close", "dividend_yield_pct", "dividend_per_share", "pe_ratio", "pb_ratio"]
COLUMNS = ["date", "market"] + [col for _, col in FIELD_KEYWORDS]


def parse_day(fields, rows, date, market):
    """Turn one day of raw rows into a clean DataFrame with English columns."""
    raw = pd.DataFrame(rows, columns=fields)
    df = pd.DataFrame(index=raw.index)
    for field in fields:
        f = field.replace(" ", "")
        for keyword, col in FIELD_KEYWORDS:
            if keyword in f and col not in df.columns:
                df[col] = raw[field]
                break
    for col in NUMERIC:
        if col in df.columns:
            df[col] = to_number(df[col])   # 'N/A' or '-' (no earnings) -> NaN
    df["code"] = df["code"].astype(str).str.strip()
    df["date"] = pd.Timestamp(date)
    df["market"] = market
    return df.reindex(columns=COLUMNS)


def fetch_day(date, market="all", client=None):
    """
    Valuation ratios on `date` ('YYYYMMDD').
    market: 'twse', 'tpex', or 'all' (both, combined).
    """
    client = client or Client()
    names = list(MARKETS) if market == "all" else [market]
    frames = []
    for name in names:
        table = MARKETS[name].valuation_day(client, date)
        if table is not None:
            frames.append(parse_day(*table, date, name))
    if not frames:
        return pd.DataFrame(columns=COLUMNS)
    return pd.concat(frames, ignore_index=True)


def top_stocks(df, n=10):
    """Highest dividend yields and lowest positive P/E ratios."""
    cols = ["market", "code", "name", "dividend_yield_pct", "pe_ratio"]
    high_yield = df.nlargest(n, "dividend_yield_pct")[cols]
    low_pe = df[df["pe_ratio"] > 0].nsmallest(n, "pe_ratio")[cols]
    return high_yield.reset_index(drop=True), low_pe.reset_index(drop=True)


def fetch_history(stock_id, days=30, market="auto", end=None, client=None):
    """
    Valuation ratios of one stock for each weekday in the last `days`
    calendar days. Weekends are skipped; holidays return no data.
    market: 'twse', 'tpex', or 'auto' (found on the first day with data).
    """
    client = client or Client()
    end = pd.Timestamp(end) if end else pd.Timestamp.today().normalize()
    dates = [d for d in pd.date_range(end=end, periods=days) if d.weekday() < 5]

    rows = []
    for d in dates:
        date = d.strftime("%Y%m%d")
        names = list(MARKETS) if market == "auto" else [market]
        found = None
        for name in names:
            print(f"{stock_id}: fetching {d:%Y-%m-%d} from {name.upper()} ...")
            day = fetch_day(date, name, client)
            match = day[day["code"] == stock_id]
            if not match.empty:
                found = match
                if market == "auto":
                    market = name          # remember the market from now on
                    print(f"{stock_id} is traded on {name.upper()}")
                break
        if found is None:
            print("  no data (holiday, or code not found)")
            continue
        rows.append(found)

    if not rows:
        return pd.DataFrame(columns=COLUMNS)
    return pd.concat(rows, ignore_index=True).sort_values("date", ignore_index=True)


def summarise_history(history):
    """Mean, min, max and latest value of dividend yield and P/E ratio."""
    stats = {}
    for col in ["dividend_yield_pct", "pe_ratio"]:
        x = history[col].dropna()
        if x.empty:
            continue
        stats[col] = {"mean": x.mean(), "min": x.min(), "max": x.max(),
                      "latest": x.iloc[-1]}
    return pd.DataFrame(stats).T.round(2)


def plot_history(history, stock_id, out_dir="output"):
    """Line charts of dividend yield and P/E ratio, saved as a PNG file."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    axes[0].plot(history["date"], history["dividend_yield_pct"], color="#0072B2")
    axes[0].set_ylabel("Dividend yield (%)")
    axes[1].plot(history["date"], history["pe_ratio"], color="#D55E00")
    axes[1].set_ylabel("P/E ratio")
    for ax in axes:
        ax.grid(True, linestyle="--", alpha=0.5)
    axes[1].xaxis.set_major_locator(mdates.AutoDateLocator(minticks=3, maxticks=10))
    axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    market = history["market"].iloc[0].upper()
    fig.suptitle(f"{stock_id} ({market}): dividend yield and P/E ratio")
    fig.autofmt_xdate()
    fig.tight_layout()

    path = Path(out_dir) / f"{stock_id}_valuation.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path
