"""
Offline tests: the HTTP client is replaced by a fake that returns responses
in the same JSON layouts as the real TWSE and TPEx endpoints, so no network
access is needed.

Run with:  python -m pytest
"""

import pandas as pd

from tw_stock_scraper import daily_prices, valuation
from tw_stock_scraper.utils import month_starts, roc_to_date, to_number

# --- fake responses (field names in Traditional Chinese, as the exchanges send them)
TWSE_DAILY_FIELDS = ["日期", "成交股數", "成交金額", "開盤價", "最高價",
                     "最低價", "收盤價", "漲跌價差", "成交筆數"]
TPEX_DAILY_FIELDS = ["日 期", "成交張數", "成交仟元", "開盤", "最高",
                     "最低", "收盤", "漲跌", "筆數"]


def twse_daily(rows):
    return {"stat": "OK", "fields": TWSE_DAILY_FIELDS, "data": rows}


def tpex_daily(rows):
    return {"stat": "ok", "tables": [{"fields": TPEX_DAILY_FIELDS, "data": rows}]}


TWSE_NO_DATA = {"stat": "很抱歉，沒有符合條件的資料!"}
TPEX_NO_DATA = {"stat": "ok", "tables": [{"fields": TPEX_DAILY_FIELDS, "data": []}]}

TWSE_VALUATION = {
    "stat": "OK",
    "fields": ["證券代號", "證券名稱", "收盤價", "殖利率(%)", "股利年度",
               "本益比", "股價淨值比", "財報年/季"],
    "data": [
        ["2330", "TSMC", "1,000.00", "1.80", "113", "25.10", "7.20", "114/2"],
        ["2882", "Cathay", "60.00", "5.00", "113", "9.50", "1.30", "114/2"],
        ["9999", "LossCo", "10.00", "0.00", "113", "-", "0.80", "114/2"],
    ],
}
TPEX_VALUATION = {
    "stat": "ok",
    "tables": [{
        "fields": ["股票代號", "名稱", "本益比", "每股股利", "股利年度",
                   "殖利率(%)", "股價淨值比"],
        "data": [
            ["6182", "WaferWorks", "N/A", "0.00000000", "113", "0.00", "1.20"],
            ["5903", "FamilyMart", "23.50", "6.50000000", "113", "7.52", "4.69"],
        ],
    }],
}


class FakeClient:
    """Routes each request to a canned response by exchange, endpoint and date."""

    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def get_json(self, url, **params):
        market = "twse" if "twse.com.tw" in url else "tpex"
        endpoint = url.rstrip("/").rsplit("/", 1)[-1]
        date = params["date"].replace("/", "")
        self.calls.append((market, endpoint, date))
        return self.responses.get((market, endpoint, date),
                                  TWSE_NO_DATA if market == "twse" else TPEX_NO_DATA)


# --- utils ---------------------------------------------------------------------
def test_roc_to_date():
    assert roc_to_date("113/09/02") == pd.Timestamp("2024-09-02")


def test_to_number_handles_commas_markers_and_placeholders():
    s = pd.Series(["35,000,000", "+2.50", "-1.00", "X0.00", "--", "N/A"])
    result = to_number(s).tolist()
    assert result[:4] == [35_000_000, 2.5, -1.0, 0.0]
    assert pd.isna(result[4]) and pd.isna(result[5])


def test_month_starts_within_one_year_and_across_years():
    assert month_starts("2025-03", "2025-05") == ["20250301", "20250401", "20250501"]
    assert month_starts("2024-12", "2025-01") == ["20241201", "20250101"]


# --- daily prices ------------------------------------------------------------------
def test_twse_and_tpex_daily_rows_give_the_same_units():
    twse = daily_prices.parse_month(TWSE_DAILY_FIELDS, [
        ["113/09/02", "5,000", "1,000,000", "200", "205", "199", "203", "+2.0", "10"]])
    tpex = daily_prices.parse_month(TPEX_DAILY_FIELDS, [
        ["113/09/02", "5", "1,000", "200", "205", "199", "203", "2.00", "10"]])
    # TPEx reports lots (1,000 shares) and thousands of TWD; both become units
    assert twse.equals(tpex)
    assert list(tpex.columns) == daily_prices.COLUMNS
    assert tpex.loc[0, "volume_shares"] == 5_000
    assert tpex.loc[0, "value_twd"] == 1_000_000


def test_tpex_legacy_layout_without_field_names():
    from tw_stock_scraper.markets import tpex
    legacy = {"aaData": [["113/09/02", "5", "1,000", "200", "205", "199",
                          "203", "2.00", "10"]]}
    fields, rows = tpex._table(legacy, tpex.LEGACY_DAILY_FIELDS)
    df = daily_prices.parse_month(fields, rows)
    assert df.loc[0, "volume_shares"] == 5_000      # 仟股 = thousands of shares


def test_auto_market_finds_tpex_stock_and_remembers_it():
    row = ["114/01/02", "5", "1,000", "200", "205", "199", "203", "2.00", "10"]
    client = FakeClient({
        ("tpex", "tradingStock", "20250101"): tpex_daily([row]),
        ("tpex", "tradingStock", "20250201"): tpex_daily([row[:0] + ["114/02/03"] + row[1:]]),
    })
    df = daily_prices.fetch_range("6182", "2025-01", "2025-02", client=client)
    assert len(df) == 2
    # Jan: TWSE (no data) then TPEx; Feb: TPEx only, no repeated detection
    assert client.calls == [("twse", "STOCK_DAY", "20250101"),
                            ("tpex", "tradingStock", "20250101"),
                            ("tpex", "tradingStock", "20250201")]


def test_update_csv_adds_new_days_and_refreshes_existing_ones(tmp_path):
    day1 = ["113/09/02", "1,000", "100", "10", "11", "9", "10.5", "+0.5", "10"]
    first = FakeClient({("twse", "STOCK_DAY", "20240901"): twse_daily([day1])})
    daily_prices.update_csv("2330", "2024-09", "2024-09", market="twse",
                            data_dir=tmp_path, client=first)

    revised = day1[:6] + ["10.6"] + day1[7:]
    day2 = ["113/09/03", "2,000", "200", "10", "12", "10", "11.0", "+0.4", "20"]
    second = FakeClient({("twse", "STOCK_DAY", "20240901"): twse_daily([revised, day2])})
    df = daily_prices.update_csv("2330", "2024-09", "2024-09", market="twse",
                                 data_dir=tmp_path, client=second)

    assert len(df) == 2
    assert df.loc[0, "close"] == 10.6        # existing day was refreshed
    assert df.loc[1, "date"] == pd.Timestamp("2024-09-03")


# --- valuation -----------------------------------------------------------------------
def test_fetch_day_combines_both_markets():
    client = FakeClient({("twse", "BWIBBU_d", "20251114"): TWSE_VALUATION,
                         ("tpex", "peQryDate", "20251114"): TPEX_VALUATION})
    df = valuation.fetch_day("20251114", client=client)
    assert list(df.columns) == valuation.COLUMNS
    assert df["market"].value_counts().to_dict() == {"twse": 3, "tpex": 2}
    assert pd.isna(df.set_index("code").loc["6182", "pe_ratio"])   # 'N/A'
    assert pd.isna(df.set_index("code").loc["9999", "pe_ratio"])   # '-'


def test_top_stocks_ranks_across_markets_and_ignores_missing_pe():
    client = FakeClient({("twse", "BWIBBU_d", "20251114"): TWSE_VALUATION,
                         ("tpex", "peQryDate", "20251114"): TPEX_VALUATION})
    df = valuation.fetch_day("20251114", client=client)
    high_yield, low_pe = valuation.top_stocks(df, n=2)
    assert list(high_yield["code"]) == ["5903", "2882"]
    assert list(low_pe["code"]) == ["2882", "5903"]


def test_fetch_history_auto_detects_tpex_and_skips_weekends_and_holidays():
    # 2025-11-10 (Mon) to 2025-11-16 (Sun); Wednesday is a holiday
    days = ["20251110", "20251111", "20251113", "20251114"]
    responses = {("tpex", "peQryDate", d): TPEX_VALUATION for d in days}
    client = FakeClient(responses)
    hist = valuation.fetch_history("5903", days=7, end="2025-11-16", client=client)
    assert len(hist) == 4
    assert set(hist["market"]) == {"tpex"}
    # TWSE is only checked on the first day; after that the market is known
    assert sum(1 for m, _, _ in client.calls if m == "twse") == 1
