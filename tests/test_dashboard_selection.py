from ohmywealth.domain.models import Asset, AssetKind
from ohmywealth.presentation.filters import asset_ids, grouped_asset_ids, toggle_group


def test_dashboard_hierarchy_toggles_real_child_accounts() -> None:
    assets = [
        Asset(1, "BANK", "Bank", AssetKind.CASH, "USD"),
        Asset(2, "HSBC-CD", "HSBC CD", AssetKind.CD, "HKD"),
        Asset(3, "AAPL", "Apple", AssetKind.STOCK, "USD"),
        Asset(4, "EURO", "Euro account", AssetKind.CASH, "EUR"),
    ]

    selected = asset_ids(assets)
    selected = toggle_group(
        selected,
        grouped_asset_ids(assets, AssetKind.CASH.value, "USD"),
        checked=False,
    )
    assert selected == {2, 3, 4}

    selected = toggle_group(
        selected,
        grouped_asset_ids(assets, AssetKind.CASH.value),
        checked=True,
    )
    assert selected == {1, 2, 3, 4}
