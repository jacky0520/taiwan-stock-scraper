"""The two Taiwanese stock markets: TWSE (listed) and TPEx (OTC)."""

from . import tpex, twse

MARKETS = {"twse": twse, "tpex": tpex}
