"""Public US bond quote adapter keyed by ISIN or CUSIP."""

import json
import re
from collections.abc import Callable
from datetime import datetime, timezone
from decimal import Decimal
from html import unescape
from urllib.request import Request, urlopen

from ohmywealth.domain.identifiers import is_valid_isin, us_cusip
from ohmywealth.domain.models import MarketValue

FetchPage = Callable[[str], str]
MapIsin = Callable[[str], dict[str, object]]


class BondMarketData:
    """Resolve bond reference data and use public quotes when available."""

    def __init__(
        self,
        public_quotes: "PublicBondData | None" = None,
        map_isin: MapIsin | None = None,
    ) -> None:
        self.public_quotes = public_quotes or PublicBondData()
        self.map_isin = map_isin or _map_openfigi

    def supports(self, identifier: str) -> bool:
        return is_valid_isin(identifier.strip().upper()) or (
            us_cusip(identifier) is not None
        )

    def metadata(self, identifier: str) -> dict[str, str]:
        identifier = identifier.strip().upper()
        if self.public_quotes.supports(identifier):
            return self.public_quotes.metadata(identifier)
        if not is_valid_isin(identifier):
            raise ValueError(f"{identifier!r} is not a valid ISIN or US CUSIP")
        result = self.map_isin(identifier)
        name = str(result.get("name") or result.get("ticker") or identifier)
        description = str(result.get("securityDescription") or "")
        security_type = str(result.get("securityType") or "")
        ticker = str(result.get("ticker") or "")
        exchange = str(result.get("exchCode") or "OTC")
        if "FXCD" in ticker.upper():
            instrument_type = "cd"
        elif exchange == "NOT LISTED":
            instrument_type = "private_bond"
        else:
            instrument_type = "bond"
        currency = "USD" if security_type == "EURO-DOLLAR" else ""
        display_name = (
            f"{name} — {description}"
            if description and name.upper() not in description.upper()
            else description or name
        )
        return {
            "symbol": identifier,
            "name": display_name,
            "exchange": exchange,
            "type": instrument_type,
            "currency": currency,
        }

    def price(self, identifier: str) -> MarketValue:
        if self.public_quotes.supports(identifier):
            return self.public_quotes.price(identifier)
        raise RuntimeError(
            f"No public market price is available for OTC bond {identifier}; "
            "the last cached quote will be used when present"
        )


class PublicBondData:
    """Read the public, server-rendered Webull US bond quote page."""

    def __init__(self, fetch_page: FetchPage | None = None) -> None:
        self.fetch_page = fetch_page or _fetch_page

    def supports(self, identifier: str) -> bool:
        return us_cusip(identifier) is not None

    def metadata(self, identifier: str) -> dict[str, str]:
        quote = self._quote(identifier)
        symbol = str(quote.get("isin") or quote.get("cusip") or identifier).upper()
        return {
            "symbol": symbol,
            "name": str(quote.get("fullName") or quote.get("name") or symbol),
            "exchange": str(quote.get("exchangeCode") or "BOND"),
            "type": "bond",
            "currency": str(quote.get("currencyCode") or "USD").upper(),
        }

    def price(self, identifier: str) -> MarketValue:
        quote = self._quote(identifier)
        value = Decimal(str(quote.get("close") or "0"))
        if value <= 0:
            raise RuntimeError(f"No positive bond price returned for {identifier}")
        observed_at = _parse_time(str(quote.get("tradeTime") or ""))
        return MarketValue(value, observed_at)

    def _quote(self, identifier: str) -> dict[str, object]:
        cusip = us_cusip(identifier)
        if cusip is None:
            raise ValueError(f"{identifier!r} is not a valid US ISIN or CUSIP")
        page = self.fetch_page(
            f"https://www.webull.com/quote/bond-{cusip.lower()}"
        )
        match = re.search(
            r'<script id="server-side-script">\s*'
            r"window\.__initState__=(.*?);?\s*</script>",
            page,
            re.DOTALL,
        )
        if match is None:
            raise RuntimeError(f"No public bond data returned for {identifier}")
        state = json.loads(unescape(match.group(1)))
        ticker_map = state.get("tickerMap", {})
        if not isinstance(ticker_map, dict) or not ticker_map:
            raise RuntimeError(f"No public bond quote returned for {identifier}")
        first = next(iter(ticker_map.values()))
        quote = first.get("tickerRT", {}) if isinstance(first, dict) else {}
        if not isinstance(quote, dict) or quote.get("cusip") != cusip:
            raise RuntimeError(f"Bond quote did not match {identifier}")
        return quote


def _fetch_page(url: str) -> str:
    request = Request(url, headers={"User-Agent": "ohmywealth/0.1"})
    with urlopen(request, timeout=15) as response:  # noqa: S310 - fixed HTTPS host
        return response.read().decode("utf-8")


def _map_openfigi(identifier: str) -> dict[str, object]:
    payload = json.dumps(
        [{"idType": "ID_ISIN", "idValue": identifier}]
    ).encode("utf-8")
    request = Request(
        "https://api.openfigi.com/v3/mapping",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "ohmywealth/0.1",
        },
        method="POST",
    )
    with urlopen(request, timeout=15) as response:  # noqa: S310 - fixed HTTPS host
        results = json.loads(response.read().decode("utf-8"))
    first = results[0] if isinstance(results, list) and results else {}
    matches = first.get("data", []) if isinstance(first, dict) else []
    if not isinstance(matches, list) or not matches:
        raise ValueError(f"No bond metadata found for ISIN {identifier}")
    result = matches[0]
    if not isinstance(result, dict):
        raise ValueError(f"Invalid bond metadata returned for ISIN {identifier}")
    return result


def _parse_time(value: str) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%f%z")
    except ValueError:
        return datetime.now(timezone.utc)
