"""Pure helpers for the dashboard's hierarchical asset selector."""

from ohmywealth.domain.models import Asset


def asset_ids(assets: list[Asset]) -> set[int]:
    return {int(asset.id) for asset in assets if asset.id is not None}


def grouped_asset_ids(
    assets: list[Asset],
    kind: str,
    currency: str | None = None,
) -> set[int]:
    return {
        int(asset.id)
        for asset in assets
        if asset.id is not None
        and asset.kind.value == kind
        and (currency is None or asset.currency == currency)
    }


def toggle_group(
    selected: set[int],
    group: set[int],
    checked: bool,
) -> set[int]:
    """Select or deselect a parent group's actual child accounts."""
    return selected | group if checked else selected - group
