import json
from decimal import Decimal

from ohmywealth.domain.identifiers import is_valid_cusip, is_valid_isin, us_cusip
from ohmywealth.infrastructure.bonds import BondMarketData, PublicBondData


def _page() -> str:
    state = {
        "tickerMap": {
            "1": {
                "tickerRT": {
                    "cusip": "91282CKR1",
                    "isin": "US91282CKR15",
                    "fullName": "United States Treasury 4.5%, 05/15/2027",
                    "currencyCode": "USD",
                    "exchangeCode": "BOND",
                    "close": "100.266",
                    "tradeTime": "2026-09-04T20:59:27.133+0000",
                }
            }
        }
    }
    return (
        '<script id="server-side-script">window.__initState__='
        + json.dumps(state)
        + ";</script>"
    )


def test_public_bond_data_resolves_isin_metadata_and_price() -> None:
    provider = PublicBondData(lambda _url: _page())

    metadata = provider.metadata("US91282CKR15")
    price = provider.price("US91282CKR15")

    assert metadata == {
        "symbol": "US91282CKR15",
        "name": "United States Treasury 4.5%, 05/15/2027",
        "exchange": "BOND",
        "type": "bond",
        "currency": "USD",
    }
    assert price.value == Decimal("100.266")
    assert price.observed_at.isoformat() == "2026-09-04T20:59:27.133000+00:00"


def test_us_bond_identifier_validation() -> None:
    assert is_valid_isin("US91282CKR15")
    assert is_valid_cusip("91282CKR1")
    assert us_cusip("US91282CKR15") == "91282CKR1"
    assert us_cusip("NOT-A-BOND") is None


def test_xs_isin_uses_openfigi_reference_metadata() -> None:
    mapped = {
        "figi": "BBG0234P1GK2",
        "name": "AGRICULTURAL BK CHINA/HK",
        "ticker": "AGRBK 3.12 09/28/26 FXCD",
        "exchCode": "NOT LISTED",
        "securityType": "EURO-DOLLAR",
        "securityDescription": "AGRBK 3.12 09/28/26",
    }
    provider = BondMarketData(map_isin=lambda _identifier: mapped)

    metadata = provider.metadata("XS3421979140")

    assert metadata == {
        "symbol": "XS3421979140",
        "name": "AGRICULTURAL BK CHINA/HK — AGRBK 3.12 09/28/26",
        "exchange": "NOT LISTED",
        "type": "cd",
        "currency": "USD",
    }


def test_unlisted_non_cd_is_classified_as_private_bond() -> None:
    mapped = {
        "name": "Example issuer",
        "ticker": "EXAMPLE 5 01/01/30",
        "exchCode": "NOT LISTED",
        "securityType": "EURO-DOLLAR",
    }
    provider = BondMarketData(map_isin=lambda _identifier: mapped)

    assert provider.metadata("XS3421979140")["type"] == "private_bond"
