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

# Column order of the older layout (Traditional Chinese, as sent by TPEx)
LEGACY_DAILY_FIELDS = ["日期", "成交仟股", "成交仟元", "開盤", "最高",
                       "最低", "收盤", "漲跌", "筆數"]
LEGACY_VALUATION_FIELDS = ["股票代號", "名稱", "本益比", "每股股利",
                           "股利年度", "殖利率(%)", "股價淨值比"]


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
