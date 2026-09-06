"""Pure helpers for expanding dashboard filter selections."""

from ohmywealth.domain.models import Asset


def selected_asset_ids(
    selected: list[str] | None,
    assets: list[Asset],
) -> set[int] | None:
    """Expand class, currency, and account tokens into asset IDs."""
    if not selected or "all" in selected:
        return None
    selected_classes = {
        token.removeprefix("class:")
        for token in selected
        if token.startswith("class:")
    }
    selected_currencies = {
        token.removeprefix("currency:")
        for token in selected
        if token.startswith("currency:")
    }
    selected_ids = {
        int(token.removeprefix("asset:"))
        for token in selected
        if token.startswith("asset:")
    }
    selected_ids.update(
        int(asset.id)
        for asset in assets
        if asset.id is not None
        and (
            asset.kind.value in selected_classes
            or asset.currency in selected_currencies
        )
    )
    return selected_ids
