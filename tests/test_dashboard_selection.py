from ohmywealth.domain.models import Asset, AssetKind
from ohmywealth.presentation.filters import selected_asset_ids


def test_dashboard_selection_expands_classes_currencies_and_accounts() -> None:
    assets = [
        Asset(1, "BANK", "Bank", AssetKind.CASH, "USD"),
        Asset(2, "HSBC-CD", "HSBC CD", AssetKind.CD, "HKD"),
        Asset(3, "AAPL", "Apple", AssetKind.STOCK, "USD"),
        Asset(4, "EURO", "Euro account", AssetKind.CASH, "EUR"),
    ]

    selected = ["class:cd", "currency:EUR", "asset:1"]
    assert selected_asset_ids(selected, assets) == {1, 2, 4}
    assert selected_asset_ids(["all"], assets) is None
