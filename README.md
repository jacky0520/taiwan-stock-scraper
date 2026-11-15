# Taiwan Stock Scraper

A small Python package that downloads and cleans public stock data from both
Taiwanese stock markets:

- **TWSE** (Taiwan Stock Exchange): listed stocks
- **TPEx** (Taipei Exchange): over-the-counter (OTC) stocks

It provides:

- **Daily prices** of a stock (open, high, low, close, volume, ...) for any
  range of months, kept up to date in a CSV file
- **Valuation ratios** (dividend yield, P/E, P/B) of every stock in both
  markets on a given day, with rankings of the highest yields and lowest P/E ratios
- **Valuation history** of one stock over recent days, with a summary and a chart

## Features

- **Automatic market detection**: give a stock code and the package finds out
  whether it trades on TWSE or TPEx
- **One consistent output format for both markets**: the two exchanges use
  different field names, layouts and units. TPEx reports volume in thousands
  of shares (or lots of 1,000 shares) and value in thousands of TWD; everything
  is converted to shares and TWD so the two markets can be compared directly
- **Data cleaning**: converts Republic of China (Minguo) dates such as
  `113/09/02` to `2024-09-02`, removes thousands separators, handles
  ex-dividend markers and missing values (`-`, `N/A`), and renames columns to English
- **Polite to the servers**: a random 3–6 second pause between requests and
  automatic retries (both exchanges temporarily block clients that request too quickly)
- **Robust HTTPS**: uses the operating system's certificate store via
  `truststore`, because the TPEx server does not always send its full certificate chain
- **Incremental updates**: re-running the price download merges new trading days
  into the existing CSV and refreshes days that changed, without duplicates
- **Offline unit tests** with fake responses in each exchange's format

## Installation

```bash
pip install -r requirements.txt
```

## Usage

Run from the project folder:

```bash
# Daily prices; the market is detected automatically
python -m tw_stock_scraper prices 2330 --start 2025-01 --end 2025-06   # TSMC (TWSE)
python -m tw_stock_scraper prices 6182 --start 2025-01 --end 2025-06   # Wafer Works (TPEx)

# Valuation ratios of all stocks in both markets on one day, with top-10 rankings
python -m tw_stock_scraper valuation --date 20251114

# Dividend yield and P/E of one stock over the last 30 days, with a chart in output/
python -m tw_stock_scraper valuation-history 2882 --days 30
```

Each command accepts `--market` to choose a market explicitly
(`twse` / `tpex`; `valuation` also accepts `all`, the default).

The functions can also be used from Python:

```python
from tw_stock_scraper import daily_prices, valuation

prices = daily_prices.fetch_range("6182", "2025-01", "2025-03")      # auto-detects TPEx
ratios = valuation.fetch_day("20251114")                              # both markets
high_yield, low_pe = valuation.top_stocks(ratios, n=10)
```

## Output columns

| Daily prices | | Valuation ratios | |
|---|---|---|---|
| `date` | trading day | `date`, `market` | trading day, `twse` or `tpex` |
| `volume_shares` | shares traded | `code`, `name` | stock code and name |
| `value_twd` | value traded (TWD) | `dividend_yield_pct` | dividend yield (%) |
| `open`, `high`, `low`, `close` | prices (TWD) | `pe_ratio` | price / earnings (empty if no earnings) |
| `change` | change from previous close | `pb_ratio` | price / book value |
| `transactions` | number of trades | `close`, `report_period` | TWSE only |
| | | `dividend_per_share` | TPEx only |

## Tests

```bash
python -m pytest
```

## Project structure

```
├── tw_stock_scraper/
│   ├── __main__.py       command-line interface
│   ├── client.py         HTTP requests with delays, retries and OS certificates
│   ├── daily_prices.py   daily prices, market detection, CSV updates
│   ├── valuation.py      yield / P/E / P/B, rankings, history chart
│   ├── utils.py          date conversion and number cleaning
│   └── markets/
│       ├── twse.py       TWSE endpoints (STOCK_DAY, BWIBBU_d)
│       └── tpex.py       TPEx endpoints (tradingStock, peQryDate)
├── tests/
│   └── test_parsing.py   offline tests with fake responses
└── requirements.txt
```

Downloaded data (`data/`) and charts (`output/`) are not stored in this repository.

## Notes

- Data comes from the [Taiwan Stock Exchange](https://www.twse.com.tw/) and the
  [Taipei Exchange](https://www.tpex.org.tw/). Please keep the request delay in
  place and check each exchange's terms of use before using the data beyond
  personal research.
- The exchanges occasionally change their endpoints or field names. Columns are
  matched by keywords rather than exact names to reduce the impact, but an
  endpoint change would need a code update.
- I first learned TWSE web scraping from a Python textbook. The code in this
  repository is a complete rewrite and does not reuse the book's examples.

## Tools

Python · requests · pandas · matplotlib · truststore · pytest
