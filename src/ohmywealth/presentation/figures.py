"""Plotly figure factories."""

from collections import defaultdict

import plotly.graph_objects as go

from ohmywealth.application.reporting import WealthReport
from ohmywealth.domain.models import AssetKind


def history_figure(report: WealthReport) -> go.Figure:
    figure = go.Figure(
        go.Scatter(
            x=[item.month for item in report.history],
            y=[float(item.total) for item in report.history],
            mode="lines+markers",
            line={"color": "#00a896", "width": 3},
        )
    )
    figure.update_layout(height=420)
    return _style(figure, "Wealth history")


def class_history_figure(report: WealthReport) -> go.Figure:
    months = [item.month for item in report.history]
    values = {
        (item.month, item.asset_class): float(item.total)
        for item in report.class_history
    }
    colors = {
        AssetKind.CASH: "#00a896",
        AssetKind.STOCK: "#4f6bed",
        AssetKind.ETF: "#f4a261",
        AssetKind.BOND: "#8f6bb3",
        AssetKind.PRIVATE_BOND: "#a785c4",
        AssetKind.CD: "#d17b88",
        AssetKind.OTHER: "#82938f",
    }
    present_classes = [
        asset_class
        for asset_class in AssetKind
        if any((month, asset_class) in values for month in months)
    ]
    figure = go.Figure(
        [
            go.Bar(
                name=asset_class.label,
                x=months,
                y=[values.get((month, asset_class), 0) for month in months],
                marker={"color": colors[asset_class]},
                hovertemplate=(
                    f"{asset_class.label}<br>%{{x|%B %Y}}"
                    "<br>%{y:,.2f}<extra></extra>"
                ),
            )
            for asset_class in present_classes
        ]
    )
    figure.update_layout(
        barmode="stack",
        height=480,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.01},
        margin={"l": 55, "r": 20, "t": 90, "b": 45},
        yaxis={"title": None, "gridcolor": "#e5eeeb"},
        xaxis={"title": None},
        hovermode="x unified",
    )
    return _style(
        figure,
        "Wealth by asset class over time"
        "<br><sup>Historical units valued at current prices and FX</sup>",
    )


def composition_figure(report: WealthReport, by: str) -> go.Figure:
    groups: dict[str, float] = defaultdict(float)
    for item in report.holdings:
        if by == "class":
            key = item.asset.kind.label
        elif item.asset.kind == AssetKind.CASH:
            key = item.asset.display_name
        else:
            key = (
                f"{item.asset.symbol} ({item.asset.nickname})"
                if item.asset.nickname
                else item.asset.symbol
            )
        groups[key] += float(item.value)

    if not groups:
        title = (
            "Composition by asset class"
            if by == "class"
            else "Composition by account or ticker"
        )
        figure = go.Figure()
        figure.add_annotation(
            text="No valued holdings in the latest completed month",
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
        )
        figure.update_layout(
            height=460,
            xaxis={"visible": False},
            yaxis={"visible": False},
        )
        return _style(figure, title)

    if by == "class":
        figure = go.Figure(
            go.Pie(
                labels=list(groups),
                values=list(groups.values()),
                hole=0.55,
                textinfo="percent",
                hovertemplate="%{label}<br>%{value:,.2f} (%{percent})<extra></extra>",
            )
        )
        figure.update_layout(
            height=460,
            legend={
                "orientation": "h",
                "yanchor": "top",
                "y": -0.08,
                "xanchor": "center",
                "x": 0.5,
            },
            margin={"l": 20, "r": 20, "t": 55, "b": 90},
        )
        return _style(figure, "Composition by asset class")

    ordered = sorted(groups.items(), key=lambda item: item[1])
    labels = [item[0] for item in ordered]
    values = [item[1] for item in ordered]
    total = sum(values)
    percentages = [value / total * 100 if total else 0 for value in values]
    figure = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker={"color": "#00a896"},
            customdata=percentages,
            text=[f"{percentage:.1f}%" for percentage in percentages],
            textposition="outside",
            hovertemplate=(
                "%{y}<br>%{x:,.2f}<br>%{customdata:.1f}% of total<extra></extra>"
            ),
        )
    )
    figure.update_layout(
        height=max(460, 100 + len(groups) * 36),
        showlegend=False,
        margin={"l": 120, "r": 65, "t": 55, "b": 45},
        xaxis={"title": None, "showgrid": True, "gridcolor": "#e5eeeb"},
        yaxis={"title": None, "automargin": True},
    )
    return _style(figure, "Composition by account or ticker")


def _style(figure: go.Figure, title: str) -> go.Figure:
    figure.update_layout(
        title=title,
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return figure
