from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import plotly.graph_objects as go
from plotly.io import to_html


def build_visual_report(run_dir: Path, out_dir: Path | None = None, *, include_plotlyjs: str | bool = "cdn") -> Path:
    run_dir = Path(run_dir)
    out_dir = Path(out_dir) if out_dir is not None else run_dir / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)

    activity_rows = load_csv(run_dir / "truth" / "canonical_activity.csv")
    site_rows = load_csv(run_dir / "master" / "sites.csv")
    report = load_json(run_dir / "generation_report.json")
    joined_rows = join_activity_with_sites(activity_rows, site_rows)

    figures = [
        ("Activity Amount Histogram", activity_histogram(joined_rows)),
        ("Activity Amount Box Plot", activity_boxplot(joined_rows)),
        ("Site Type Distribution", site_type_boxplot(joined_rows)),
        ("Monthly Activity Trend", monthly_trend(joined_rows)),
    ]

    html = render_dashboard(
        title="Synthetic ESG Distribution Report",
        run_dir=run_dir,
        distribution_stats=report.get("distribution_stats", {}),
        record_counts=report.get("record_counts", {}),
        figures=figures,
        include_plotlyjs=include_plotlyjs,
    )
    out_path = out_dir / "distribution_dashboard.html"
    out_path.write_text(html, encoding="utf-8")
    return out_path


def load_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def join_activity_with_sites(activity_rows: list[dict[str, Any]], site_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sites_by_id = {row["site_id"]: row for row in site_rows}
    joined: list[dict[str, Any]] = []
    for row in activity_rows:
        out = dict(row)
        site = sites_by_id.get(str(row.get("site_id")), {})
        out["site_type"] = site.get("site_type", "unknown")
        out["country"] = site.get("country", "unknown")
        out["standardized_amount"] = parse_float(row.get("standardized_amount"))
        out["period"] = period_from_period_id(str(row.get("period_id", "")))
        joined.append(out)
    return joined


def parse_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def period_from_period_id(period_id: str) -> str:
    token = period_id.removeprefix("P-").removeprefix("P")
    if len(token) == 6 and token.isdigit():
        return f"{token[:4]}-{token[4:]}"
    return period_id


def activity_histogram(rows: list[dict[str, Any]]) -> go.Figure:
    fig = go.Figure()
    for activity_type in sorted({str(row.get("activity_type", "unknown")) for row in rows}):
        values = [row["standardized_amount"] for row in rows if row.get("activity_type") == activity_type]
        fig.add_trace(go.Histogram(x=values, name=activity_type, opacity=0.72, nbinsx=60))
    fig.update_layout(
        title="Activity Amount Distribution",
        xaxis_title="standardized_amount",
        yaxis_title="row count",
        barmode="overlay",
        yaxis_type="log",
    )
    return fig


def activity_boxplot(rows: list[dict[str, Any]]) -> go.Figure:
    fig = go.Figure()
    for activity_type in sorted({str(row.get("activity_type", "unknown")) for row in rows}):
        values = [row["standardized_amount"] for row in rows if row.get("activity_type") == activity_type]
        fig.add_trace(go.Box(y=values, name=activity_type, boxpoints="outliers"))
    fig.update_layout(
        title="Activity Amount Box Plot",
        yaxis_title="standardized_amount",
        yaxis_type="log",
    )
    return fig


def site_type_boxplot(rows: list[dict[str, Any]]) -> go.Figure:
    fig = go.Figure()
    site_types = sorted({str(row.get("site_type", "unknown")) for row in rows})
    activities = sorted({str(row.get("activity_type", "unknown")) for row in rows})
    for activity_type in activities:
        x_values = []
        y_values = []
        for row in rows:
            if row.get("activity_type") == activity_type:
                x_values.append(str(row.get("site_type", "unknown")))
                y_values.append(row["standardized_amount"])
        fig.add_trace(go.Box(x=x_values, y=y_values, name=activity_type, boxpoints=False))
    fig.update_layout(
        title="Site Type × Activity Distribution",
        xaxis_title="site_type",
        yaxis_title="standardized_amount",
        yaxis_type="log",
        boxmode="group",
    )
    return fig


def monthly_trend(rows: list[dict[str, Any]]) -> go.Figure:
    totals: dict[tuple[str, str], float] = {}
    for row in rows:
        key = (str(row.get("period", "unknown")), str(row.get("activity_type", "unknown")))
        totals[key] = totals.get(key, 0.0) + float(row.get("standardized_amount", 0.0))

    fig = go.Figure()
    activity_types = sorted({activity for _, activity in totals})
    for activity_type in activity_types:
        points = sorted((period, total) for (period, activity), total in totals.items() if activity == activity_type)
        fig.add_trace(
            go.Scatter(
                x=[period for period, _ in points],
                y=[total for _, total in points],
                mode="lines+markers",
                name=activity_type,
            )
        )
    fig.update_layout(
        title="Monthly Activity Trend",
        xaxis_title="period",
        yaxis_title="total standardized_amount",
    )
    return fig


def render_dashboard(
    *,
    title: str,
    run_dir: Path,
    distribution_stats: dict[str, Any],
    record_counts: dict[str, Any],
    figures: list[tuple[str, go.Figure]],
    include_plotlyjs: str | bool,
) -> str:
    stats_table = render_distribution_stats(distribution_stats)
    counts_table = render_record_counts(record_counts)
    figure_html = []
    for index, (heading, fig) in enumerate(figures):
        include_js = include_plotlyjs if index == 0 else False
        figure_html.append(
            f"<section><h2>{escape_html(heading)}</h2>"
            + to_html(fig, full_html=False, include_plotlyjs=include_js)
            + "</section>"
        )

    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <title>{escape_html(title)}</title>
  <style>
    body {{ font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 32px; }}
    h1 {{ margin-bottom: 0.2rem; }}
    .muted {{ color: #666; margin-top: 0; }}
    section {{ margin-top: 32px; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 12px; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: right; }}
    th:first-child, td:first-child {{ text-align: left; }}
    th {{ background: #f6f6f6; }}
  </style>
</head>
<body>
  <h1>{escape_html(title)}</h1>
  <p class=\"muted\">Run directory: {escape_html(str(run_dir))}</p>
  <section>
    <h2>Distribution Stats</h2>
    {stats_table}
  </section>
  <section>
    <h2>Record Counts</h2>
    {counts_table}
  </section>
  {''.join(figure_html)}
</body>
</html>
"""


def render_distribution_stats(distribution_stats: dict[str, Any]) -> str:
    if not distribution_stats:
        return "<p>No distribution stats found.</p>"
    headers = ["activity_type", "count", "min", "mean", "p50", "p95", "p99", "max"]
    rows = []
    for activity_type, stats in sorted(distribution_stats.items()):
        rows.append([activity_type] + [stats.get(header, "") for header in headers[1:]])
    return render_table(headers, rows)


def render_record_counts(record_counts: dict[str, Any]) -> str:
    if not record_counts:
        return "<p>No record counts found.</p>"
    rows = [[key, value] for key, value in sorted(record_counts.items())]
    return render_table(["path", "rows"], rows)


def render_table(headers: list[str], rows: list[list[Any]]) -> str:
    header_html = "".join(f"<th>{escape_html(header)}</th>" for header in headers)
    body_rows = []
    for row in rows:
        cells = "".join(f"<td>{escape_html(str(value))}</td>" for value in row)
        body_rows.append(f"<tr>{cells}</tr>")
    return f"<table><thead><tr>{header_html}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"


def escape_html(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )
