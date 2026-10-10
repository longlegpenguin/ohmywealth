"""Plotly figure factories."""

from calendar import monthrange
from collections import defaultdict
from datetime import date
from math import ceil

import plotly.graph_objects as go

from ohmywealth.application.reporting import AccountChange, WealthReport
from ohmywealth.domain.models import AssetKind


def history_figure(
    report: WealthReport,
    start: date | None = None,
    end: date | None = None,
) -> go.Figure:
    history = [
        item
        for item in report.history
        if _in_range(_month_end(item.month), start, end)
    ]
    months = [_month_end(item.month) for item in history]
    figure = go.Figure(
        go.Scatter(
            x=months,
            y=[float(item.total) for item in history],
            mode="lines+markers",
            line={"color": "#00a896", "width": 3},
            hovertemplate="%{x|%Y-%m-%d}<br>%{y:,.2f}<extra></extra>",
        )
    )
    figure.update_layout(height=420, xaxis=_monthly_axis(months))
    return _style(figure, "Wealth history")


def class_history_figure(
    report: WealthReport,
    start: date | None = None,
    end: date | None = None,
) -> go.Figure:
    months = [
        _month_end(item.month)
        for item in report.history
        if _in_range(_month_end(item.month), start, end)
    ]
    values = {
        (_month_end(item.month), item.asset_class): float(item.total)
        for item in report.class_history
        if _in_range(_month_end(item.month), start, end)
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
        xaxis=_monthly_axis(months),
        hovermode="x unified",
    )
    return _style(
        figure,
        "Wealth by asset class over time"
        "<br><sup>Historical units valued at current prices and FX</sup>",
    )


def account_change_figure(report: WealthReport) -> go.Figure:
    """Show the selected snapshot's changes as a diverging account bar chart."""
    subtitle = "Current prices and FX"
    if report.snapshot_month is not None and report.comparison_month is not None:
        subtitle = (
            f"{report.comparison_month:%B %Y} → "
            f"{report.snapshot_month:%B %Y} · {subtitle}"
        )
    empty_text = "No account values changed since the preceding snapshot"
    if report.snapshot_month is None:
        empty_text = "No snapshot exists for the selected month"
    elif report.comparison_month is None:
        empty_text = "No preceding snapshot is available for comparison"
    return _account_change_bar(
        report.account_changes,
        "Monthly change by account",
        subtitle,
        empty_text,
    )


def overall_account_change_figure(
    report: WealthReport,
    start: date | None,
    end: date | None,
) -> go.Figure:
    """Show account changes across the selected history range."""
    months = [
        item.month
        for item in report.history
        if (start is None or item.month >= start)
        and (end is None or item.month <= end)
    ]
    subtitle = "Selected range · current prices and FX"
    if len(months) > 1:
        subtitle = f"{months[0]:%B %Y} → {months[-1]:%B %Y} · current prices and FX"
    empty_text = (
        "Select a range containing at least two snapshots"
        if len(months) < 2
        else "No account values changed across the selected range"
    )
    return _account_change_bar(
        report.account_changes_between(start, end),
        "Overall change by account",
        subtitle,
        empty_text,
    )


def _account_change_bar(
    changes: tuple[AccountChange, ...],
    title: str,
    subtitle: str,
    empty_text: str,
) -> go.Figure:
    ordered = sorted(changes, key=lambda item: item.change)
    if not ordered:
        figure = go.Figure()
        figure.add_annotation(
            text=empty_text,
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
        )
        figure.update_layout(
            height=360,
            xaxis={"visible": False},
            yaxis={"visible": False},
        )
        return _style(figure, title)

    values = [float(item.change) for item in ordered]
    labels = [item.asset.display_name for item in ordered]
    figure = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker={
                "color": ["#1b9e77" if value > 0 else "#d95f59" for value in values]
            },
            text=[f"{value:+,.2f}" for value in values],
            textposition=["inside" if value < 0 else "outside" for value in values],
            insidetextanchor="middle",
            insidetextfont={"color": "white"},
            outsidetextfont={"color": "#16302b"},
            cliponaxis=False,
            hovertemplate="%{y}<br>%{x:+,.2f}<extra></extra>",
        )
    )
    figure.update_layout(
        height=max(360, 120 + len(ordered) * 38),
        showlegend=False,
        margin={"l": 135, "r": 85, "t": 75, "b": 45},
        xaxis={
            "title": None,
            "showgrid": True,
            "gridcolor": "#e5eeeb",
            "zeroline": True,
            "zerolinecolor": "#82938f",
            "zerolinewidth": 1,
        },
        yaxis={"title": None, "automargin": True},
    )
    return _style(
        figure,
        f"{title}<br><sup>{subtitle}</sup>",
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
            text="No valued holdings in the selected month",
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


def _month_end(month: date) -> date:
    """Map the normalized storage key to the represented month-end date."""
    return month.replace(day=monthrange(month.year, month.month)[1])


def _in_range(value: date, start: date | None, end: date | None) -> bool:
    return (start is None or value >= start) and (end is None or value <= end)


def _monthly_axis(months: list[date]) -> dict[str, object]:
    """Show readable month labels instead of Plotly's automatic day ticks."""
    if not months:
        return {"title": None}
    step = max(1, ceil(len(months) / 12))
    tick_values = months[::step]
    if tick_values[-1] != months[-1]:
        tick_values.append(months[-1])
    return {
        "title": None,
        "tickmode": "array",
        "tickvals": tick_values,
        "ticktext": [month.strftime("%b %Y") for month in tick_values],
        "showgrid": False,
    }
