"""
Taipei Exchange (TPEx): over-the-counter (OTC) stocks.

Each function returns (field_names, rows), or None when there is no data.

TPEx has used two response layouts: the current site returns
{"tables": [{"fields": [...], "data": [...]}]}, while older endpoints returned
{"aaData": [...]} without field names. Both are accepted; for the older layout
the documented column order is used.
"""

NAME = "tpex"
BASE_URL = "https://www.tpex.org.tw/www/zh-tw/afterTrading/"

# Column order of the older layout. The names must stay exactly as TPEx sends
# them (Traditional Chinese) so they can be matched; they are translated to
# English column names in daily_prices.py and valuation.py.
LEGACY_DAILY_FIELDS = [
    "日期",      # date
    "成交仟股",  # volume, thousands of shares
    "成交仟元",  # value, thousands of TWD
    "開盤",      # open
    "最高",      # high
    "最低",      # low
    "收盤",      # close
    "漲跌",      # change
    "筆數",      # number of trades
]
LEGACY_VALUATION_FIELDS = [
    "股票代號",    # stock code
    "名稱",        # name
    "本益比",      # P/E ratio
    "每股股利",    # dividend per share
    "股利年度",    # dividend year
    "殖利率(%)",   # dividend yield (%)
    "股價淨值比",  # P/B ratio
]


def _table(payload, legacy_fields):
    if not payload:
        return None
    if payload.get("tables"):
        table = payload["tables"][0]
        rows = table.get("data") or []
        fields = table.get("fields") or legacy_fields
    else:
        rows = payload.get("aaData") or []
        fields = legacy_fields
    if not rows:
        return None
    return fields, rows


def _slash_date(yyyymmdd):
    return f"{yyyymmdd[:4]}/{yyyymmdd[4:6]}/{yyyymmdd[6:]}"


def daily_month(client, stock_id, month_start):
    """Every trading day of one month. `month_start` is 'YYYYMMDD'."""
    payload = client.get_json(BASE_URL + "tradingStock", code=stock_id,
                              date=_slash_date(month_start), response="json")
    return _table(payload, LEGACY_DAILY_FIELDS)


def valuation_day(client, date):
    """Dividend yield, P/E and P/B of all OTC stocks. `date` is 'YYYYMMDD'."""
    payload = client.get_json(BASE_URL + "peQryDate", date=_slash_date(date),
                              response="json")
    return _table(payload, LEGACY_VALUATION_FIELDS)
