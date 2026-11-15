"""
Command-line interface.

Examples
--------
Daily prices; the market (TWSE or TPEx) is detected automatically:
    python -m tw_stock_scraper prices 2330 --start 2025-01 --end 2025-06
    python -m tw_stock_scraper prices 6182 --start 2025-01 --end 2025-06

Highest dividend yields and lowest P/E ratios across both markets on one day:
    python -m tw_stock_scraper valuation --date 20251114

Dividend yield and P/E history of one stock over the last 30 days:
    python -m tw_stock_scraper valuation-history 2882 --days 30
"""

import argparse
from pathlib import Path

import pandas as pd

from . import daily_prices, valuation
from .client import Client


def cmd_prices(args):
    end = args.end or pd.Timestamp.today().strftime("%Y-%m")
    df = daily_prices.update_csv(args.stock_id, args.start, end, market=args.market,
                                 data_dir=args.data_dir, client=Client())
    if not df.empty:
        print(df.tail())


def cmd_valuation(args):
    date = args.date or pd.Timestamp.today().strftime("%Y%m%d")
    df = valuation.fetch_day(date, market=args.market)
    if df.empty:
        print(f"No data for {date} (weekend or holiday?)")
        return
    path = Path(args.data_dir) / f"valuation_{date}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    counts = df["market"].str.upper().value_counts().to_dict()
    print(f"Saved {len(df)} stocks {counts} to {path}")

    high_yield, low_pe = valuation.top_stocks(df, n=args.top)
    print(f"\nTop {args.top} by dividend yield:")
    print(high_yield.to_string(index=False))
    print(f"\nTop {args.top} by lowest positive P/E ratio:")
    print(low_pe.to_string(index=False))


def cmd_valuation_history(args):
    history = valuation.fetch_history(args.stock_id, days=args.days, market=args.market)
    if history.empty:
        print("No data found.")
        return
    path = Path(args.data_dir) / f"{args.stock_id}_valuation_history.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    history.to_csv(path, index=False)
    print(f"Saved {len(history)} days to {path}\n")
    print(valuation.summarise_history(history))
    chart = valuation.plot_history(history, args.stock_id, out_dir=args.out_dir)
    print(f"\nChart saved to {chart}")


def main():
    parser = argparse.ArgumentParser(prog="python -m tw_stock_scraper",
                                     description="Download Taiwan stock data "
                                                 "from TWSE and TPEx.")
    parser.add_argument("--data-dir", default="data", help="folder for CSV files")
    parser.add_argument("--out-dir", default="output", help="folder for charts")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("prices", help="daily prices of one stock")
    p.add_argument("stock_id", help="stock code, e.g. 2330 (TWSE) or 6182 (TPEx)")
    p.add_argument("--start", required=True, help="first month, YYYY-MM")
    p.add_argument("--end", help="last month, YYYY-MM (default: this month)")
    p.add_argument("--market", choices=["auto", "twse", "tpex"], default="auto")
    p.set_defaults(func=cmd_prices)

    p = sub.add_parser("valuation", help="yield / P/E / P/B of all stocks on one day")
    p.add_argument("--date", help="YYYYMMDD (default: today)")
    p.add_argument("--top", type=int, default=10, help="rows in each ranking")
    p.add_argument("--market", choices=["all", "twse", "tpex"], default="all")
    p.set_defaults(func=cmd_valuation)

    p = sub.add_parser("valuation-history", help="yield and P/E of one stock over time")
    p.add_argument("stock_id", help="stock code")
    p.add_argument("--days", type=int, default=30, help="calendar days to look back")
    p.add_argument("--market", choices=["auto", "twse", "tpex"], default="auto")
    p.set_defaults(func=cmd_valuation_history)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
