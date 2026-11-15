"""
Taiwan Stock Exchange (TWSE): listed stocks.

Each function returns (field_names, rows) as sent by the exchange,
or None when there is no data (holiday, unknown code, ...).
"""

NAME = "twse"
BASE_URL = "https://www.twse.com.tw/exchangeReport/"


def _table(payload):
    if not payload or payload.get("stat") != "OK" or not payload.get("data"):
        return None
    return payload["fields"], payload["data"]


def daily_month(client, stock_id, month_start):
    """Every trading day of one month. `month_start` is 'YYYYMMDD'."""
    payload = client.get_json(BASE_URL + "STOCK_DAY", response="json",
                              date=month_start, stockNo=stock_id)
    return _table(payload)


def valuation_day(client, date):
    """Dividend yield, P/E and P/B of all listed stocks. `date` is 'YYYYMMDD'."""
    payload = client.get_json(BASE_URL + "BWIBBU_d", response="json",
                              date=date, selectType="ALL")
    return _table(payload)
