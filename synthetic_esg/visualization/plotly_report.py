from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import plotly.graph_objects as go
from plotly.io import to_html


REPORT_COLORWAY = ["#0f766e", "#2563eb", "#b45309", "#6d28d9", "#b42318", "#64748b"]

FIGURE_METADATA: dict[str, dict[str, str]] = {
    "Activity Amount Histogram": {
        "chart_type": "Histogram",
        "purpose": "Shows where generated activity amounts are concentrated.",
        "why": "Run this to check whether generated values cluster in a plausible range or pile up in an unnatural way.",
        "read": "Tall bars show ranges that contain many records. A long right tail or isolated bar can point to unusually large generated values.",
        "check": "If the far-right values look too separated, compare them with activity type, site type, and period in the next charts.",
    },
    "Activity Amount Box Plot": {
        "chart_type": "Box plot",
        "purpose": "Compares typical ranges and outliers by activity type.",
        "why": "Run this to see whether one activity type is much wider, smaller, or more extreme than the others.",
        "read": "The box shows the usual middle range. Points beyond the whiskers are outliers that deserve a closer look.",
        "check": "Large outliers should be checked against source files to decide whether they are intended stress data or accidental noise.",
    },
    "Site Type Distribution": {
        "chart_type": "Grouped box plot",
        "purpose": "Checks whether site categories have noticeably different activity ranges.",
        "why": "Run this to confirm that plants, warehouses, and other site types produce different but reasonable activity patterns.",
        "read": "Compare boxes within each site type. Large separation can be expected for some site types, but extreme gaps may need review.",
        "check": "If one site type dominates, inspect site metadata and source mix before treating the pattern as valid.",
    },
    "Monthly Activity Trend": {
        "chart_type": "Line chart",
        "purpose": "Shows whether generated activity totals move plausibly over time.",
        "why": "Run this to find sudden jumps, drops, or flat lines that may indicate unrealistic generation behavior.",
        "read": "Each line is an activity type. A smooth change is usually easier to trust than abrupt movement without a known reason.",
        "check": "If a line jumps sharply, compare the period with injected anomalies and source record counts.",
    },
}

GLOSSARY: dict[str, dict[str, str]] = {
    "distribution": {
        "term": "Distribution",
        "definition": "How values are spread across a range.",
        "context": "In this report, distribution helps reveal whether generated values look balanced, clustered, or unusually extreme.",
    },
    "outlier": {
        "term": "Outlier",
        "definition": "A value that is much larger or smaller than most other values.",
        "context": "An outlier can be a real rare case, an injected anomaly, or a sign that generated data needs review.",
    },
    "log-scale": {
        "term": "Log scale",
        "definition": "An axis scale that compresses very large ranges so small and large values can be compared together.",
        "context": "Several ESG activity values differ by orders of magnitude, so log scale makes the chart readable.",
    },
    "histogram": {
        "term": "Histogram",
        "definition": "A chart that groups numeric values into ranges and counts how many records fall in each range.",
        "context": "It answers the question: where do most generated activity amounts land?",
    },
    "box-plot": {
        "term": "Box plot",
        "definition": "A compact chart for comparing typical ranges, spread, and outliers.",
        "context": "It helps compare activity types without reading every individual row.",
    },
    "trend": {
        "term": "Trend",
        "definition": "A pattern of movement over time.",
        "context": "The trend chart checks whether monthly totals move in a plausible direction.",
    },
    "activity-type": {
        "term": "Activity type",
        "definition": "The kind of ESG activity being measured, such as electricity, gas, steam, or diesel.",
        "context": "Comparing activity types helps spot whether one generated source behaves differently from the rest.",
    },
    "standardized-amount": {
        "term": "Standardized amount",
        "definition": "A value converted into a common unit so records from different sources can be compared.",
        "context": "This report uses standardized amounts to compare generated activity records consistently.",
    },
}


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
        xaxis_title="Standardized activity amount",
        yaxis_title="Records",
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
        yaxis_title="Standardized activity amount",
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
        title="Site Type by Activity Distribution",
        xaxis_title="Site type",
        yaxis_title="Standardized activity amount",
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
        xaxis_title="Period",
        yaxis_title="Total standardized activity amount",
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
    record_total = sum(value for value in record_counts.values() if isinstance(value, int))
    figure_html = []
    for index, (heading, fig) in enumerate(figures):
        apply_report_style(fig)
        include_js = include_plotlyjs if index == 0 else False
        plot_html = to_html(
            fig,
            full_html=False,
            include_plotlyjs=include_js,
            config={"responsive": True, "displaylogo": False},
        )
        figure_html.append(
            render_analysis_card(index + 1, heading, plot_html)
        )

    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>{escape_html(title)}</title>
  <style>
    {report_css()}
  </style>
</head>
<body>
  <div class=\"report-shell\">
    <main class=\"analysis-guide\" aria-labelledby=\"report-title\">
      <header class=\"report-hero\">
        <div>
          <p class=\"eyebrow\">Synthetic ESG</p>
          <h1 id=\"report-title\">{escape_html(title)}</h1>
          <p class=\"subtitle\">
            Analysis reading guide for checking whether generated ESG activity data has plausible ranges,
            patterns, and follow-up signals.
          </p>
        </div>
        <div class=\"summary-chips\" aria-label=\"Report summary\">
          <span>{len(figures)} analyses</span>
          <span>{record_total} recorded rows</span>
          <span>{escape_html(run_dir.name or str(run_dir))}</span>
        </div>
      </header>

      <section class=\"guide-card\" aria-labelledby=\"guide-title\">
        <p class=\"eyebrow\">Analysis reading guide</p>
        <h2 id=\"guide-title\">How to use this report</h2>
        <div class=\"guide-grid\">
          <div>
            <h3>1. Start with the chart question</h3>
            <p>Each card explains why the analysis is run before showing the Plotly chart.</p>
          </div>
          <div>
            <h3>2. Read the follow-up check</h3>
            <p>Use the follow-up note to decide which source, site, period, or activity type needs review.</p>
          </div>
          <div>
            <h3>3. Open term help as needed</h3>
            <p>Terms with dotted underlines can be opened by hover, click, tap, or keyboard focus.</p>
          </div>
        </div>
      </section>

      {render_glossary_panel()}
      {''.join(figure_html)}
    </main>

    {render_developer_drawer(run_dir, stats_table, counts_table)}
  </div>
  <div class=\"term-popover\" id=\"term-popover\" role=\"dialog\" aria-live=\"polite\" hidden></div>
  <script>
    {report_script()}
  </script>
</body>
</html>
"""


def apply_report_style(fig: go.Figure) -> None:
    fig.update_layout(
        template="plotly_white",
        colorway=REPORT_COLORWAY,
        font={"family": "Inter, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif", "color": "#202421"},
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        hoverlabel={"bgcolor": "#18201d", "font_color": "#e5eee9", "bordercolor": "#18201d"},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "left", "x": 0},
        margin={"l": 64, "r": 24, "t": 68, "b": 56},
    )
    fig.update_xaxes(gridcolor="#d7dfd8", zerolinecolor="#d7dfd8", linecolor="#9bb2a5")
    fig.update_yaxes(gridcolor="#d7dfd8", zerolinecolor="#d7dfd8", linecolor="#9bb2a5")


def render_analysis_card(index: int, heading: str, plot_html: str) -> str:
    metadata = FIGURE_METADATA.get(
        heading,
        {
            "chart_type": "Plotly chart",
            "purpose": "Shows a generated ESG data pattern.",
            "why": "Run this to inspect generated data quality.",
            "read": "Read the chart by comparing the main visual patterns.",
            "check": "Review source files if the pattern looks unexpected.",
        },
    )
    section_id = slugify(heading)
    return f"""
      <section class=\"analysis-card\" id=\"{section_id}\" aria-labelledby=\"{section_id}-title\">
        <div class=\"analysis-heading\">
          <div>
            <p class=\"eyebrow\">Analysis {index}</p>
            <h2 id=\"{section_id}-title\">{escape_html(heading)}</h2>
            <p class=\"analysis-purpose\">{escape_html(metadata["purpose"])}</p>
          </div>
          <span class=\"chart-type\">{escape_html(metadata["chart_type"])}</span>
        </div>
        <div class=\"analysis-notes\">
          <div class=\"note-block why-run-this\">
            <h3>Why run this?</h3>
            <p>{escape_html(metadata["why"])}</p>
          </div>
          <div class=\"note-block how-to-read-this\">
            <h3>How to read this</h3>
            <p>{escape_html(metadata["read"])}</p>
          </div>
          <div class=\"note-block follow-up what-to-check-next\">
            <h3>What should I check next?</h3>
            <p>{escape_html(metadata["check"])}</p>
          </div>
        </div>
        <div class=\"plot-panel\">{plot_html}</div>
      </section>
    """


def render_glossary_panel() -> str:
    triggers = " ".join(render_term_trigger(key) for key in GLOSSARY)
    return f"""
      <section class=\"glossary-panel\" aria-labelledby=\"glossary-title\">
        <div>
          <p class=\"eyebrow\">Term help</p>
          <h2 id=\"glossary-title\">Open explanations as you read</h2>
          <p>
            Specialized terms are available inline by hover, click, tap, or keyboard focus.
            {render_term_trigger("distribution")}, {render_term_trigger("outlier")}, and
            {render_term_trigger("log-scale")} are common starting points.
          </p>
        </div>
        <div class=\"term-list\" aria-label=\"Glossary terms\">{triggers}</div>
      </section>
    """


def render_term_trigger(key: str) -> str:
    item = GLOSSARY[key]
    term = escape_html(item["term"])
    return (
        f"<button type=\"button\" class=\"term-trigger\" data-term=\"{escape_html(key)}\" "
        f"aria-describedby=\"term-popover\">{term}</button>"
    )


def render_developer_drawer(run_dir: Path, stats_table: str, counts_table: str) -> str:
    return f"""
    <aside class=\"developer-drawer\" id=\"developer-drawer\" aria-label=\"Developer information\">
      <button
        class=\"developer-toggle\"
        type=\"button\"
        aria-controls=\"developer-drawer\"
        aria-expanded=\"false\"
        onclick=\"toggleDeveloperDrawer()\"
      >
        Developer information
      </button>
      <div class=\"developer-content\">
        <p class=\"eyebrow\">Developer information</p>
        <h2>Generated artifacts</h2>
        <div class=\"developer-section\">
          <h3>Run directory</h3>
          <pre>{escape_html(str(run_dir))}</pre>
        </div>
        <div class=\"developer-section\">
          <h3>Distribution stats</h3>
          {stats_table}
        </div>
        <div class=\"developer-section\">
          <h3>Record counts</h3>
          {counts_table}
        </div>
      </div>
    </aside>
    """


def report_css() -> str:
    return """
    :root {
      color-scheme: light;
      --bg: #f5f7f4;
      --surface: #ffffff;
      --surface-muted: #eef3ef;
      --border: #d7dfd8;
      --text: #202421;
      --muted: #657064;
      --accent: #0f766e;
      --accent-strong: #115e59;
      --accent-soft: #d8f3ee;
      --amber: #b45309;
      --amber-soft: #fff3d6;
      --red: #b42318;
      --red-soft: #fee4e2;
      --shadow: 0 16px 40px rgba(32, 36, 33, 0.08);
    }

    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    button { font: inherit; }
    h1, h2, h3, p { margin-top: 0; }
    h1 { font-size: clamp(2rem, 4vw, 3.2rem); line-height: 1.05; margin-bottom: 10px; }
    h2 { font-size: 1.25rem; line-height: 1.2; margin-bottom: 6px; }
    h3 { font-size: 0.95rem; line-height: 1.25; margin-bottom: 6px; }
    table { border-collapse: collapse; font-size: 0.78rem; width: 100%; }
    th, td { border-bottom: 1px solid var(--border); padding: 7px 8px; text-align: right; }
    th:first-child, td:first-child { text-align: left; }
    th { background: var(--surface-muted); color: var(--muted); font-weight: 800; }
    pre {
      background: #18201d;
      border-radius: 8px;
      color: #e5eee9;
      font-size: 0.78rem;
      line-height: 1.5;
      overflow: auto;
      padding: 12px;
      white-space: pre-wrap;
    }
    .report-shell {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      min-height: 100vh;
    }
    .analysis-guide {
      display: grid;
      gap: 18px;
      margin: 0 auto;
      max-width: 1180px;
      padding: 28px;
      width: 100%;
    }
    .report-hero, .guide-card, .glossary-panel, .analysis-card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 8px;
      box-shadow: var(--shadow);
      padding: 18px;
    }
    .report-hero {
      align-items: flex-start;
      display: flex;
      gap: 18px;
      justify-content: space-between;
    }
    .eyebrow {
      color: var(--accent);
      font-size: 0.74rem;
      font-weight: 800;
      letter-spacing: 0;
      margin-bottom: 6px;
      text-transform: uppercase;
    }
    .subtitle, .analysis-purpose, .note-block p, .guide-card p, .glossary-panel p {
      color: var(--muted);
      line-height: 1.55;
      margin-bottom: 0;
    }
    .summary-chips, .term-list {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
    .summary-chips span, .chart-type {
      background: var(--surface-muted);
      border-radius: 999px;
      color: var(--muted);
      font-size: 0.82rem;
      font-weight: 800;
      padding: 7px 10px;
      white-space: nowrap;
    }
    .guide-grid, .analysis-notes {
      display: grid;
      gap: 10px;
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }
    .guide-grid > div, .note-block {
      background: var(--surface-muted);
      border-radius: 8px;
      padding: 12px;
    }
    .analysis-heading {
      align-items: flex-start;
      display: flex;
      gap: 12px;
      justify-content: space-between;
      margin-bottom: 14px;
    }
    .follow-up {
      background: var(--amber-soft);
      border: 1px solid #f0d28a;
    }
    .follow-up h3, .follow-up p { color: #8a4b05; }
    .plot-panel {
      border: 1px solid var(--border);
      border-radius: 8px;
      margin-top: 14px;
      overflow: hidden;
      padding: 8px;
    }
    .plotly-graph-div { min-height: 440px; }
    .term-trigger {
      background: transparent;
      border: 0;
      border-bottom: 1px dotted var(--accent);
      color: var(--accent);
      cursor: help;
      display: inline;
      font-weight: 800;
      padding: 0;
    }
    .term-trigger:focus-visible {
      outline: 2px solid var(--accent);
      outline-offset: 3px;
    }
    .term-popover {
      background: #18201d;
      border: 1px solid #2e3a35;
      border-radius: 8px;
      box-shadow: 0 18px 50px rgba(24, 32, 29, 0.28);
      color: #e5eee9;
      max-width: min(360px, calc(100vw - 32px));
      padding: 12px;
      position: fixed;
      z-index: 10;
    }
    .term-popover h3 { color: #ffffff; margin-bottom: 6px; }
    .term-popover p { color: #c7d4ce; line-height: 1.5; margin: 0; }
    .developer-drawer {
      background: #18201d;
      bottom: 0;
      box-shadow: -18px 0 42px rgba(24, 32, 29, 0.16);
      color: #e5eee9;
      max-width: min(460px, calc(100vw - 40px));
      position: fixed;
      right: 0;
      top: 0;
      transform: translateX(calc(100% - 48px));
      transition: transform 160ms ease;
      width: 460px;
      z-index: 9;
    }
    .developer-drawer.is-open { transform: translateX(0); }
    .developer-toggle {
      align-items: center;
      background: #18201d;
      border: 0;
      border-left: 1px solid #2e3a35;
      color: #e5eee9;
      cursor: pointer;
      display: flex;
      font-size: 0.75rem;
      font-weight: 900;
      height: 100%;
      justify-content: center;
      left: 0;
      padding: 8px;
      position: absolute;
      top: 0;
      width: 48px;
      writing-mode: vertical-rl;
    }
    .developer-content {
      display: grid;
      gap: 14px;
      height: 100%;
      margin-left: 48px;
      overflow: auto;
      padding: 22px;
    }
    .developer-content h2, .developer-content h3 { color: #ffffff; }
    .developer-section {
      border-top: 1px solid #2e3a35;
      padding-top: 12px;
    }
    .developer-section table { color: #e5eee9; }
    .developer-section th { background: #26302c; color: #aebdb5; }
    .developer-section td, .developer-section th { border-color: #2e3a35; }

    @media (max-width: 860px) {
      .analysis-guide { padding: 16px; }
      .report-hero, .analysis-heading { display: grid; }
      .guide-grid, .analysis-notes { grid-template-columns: 1fr; }
      .plotly-graph-div { min-height: 360px; }
    }
    """


def report_script() -> str:
    glossary_json = json.dumps(GLOSSARY, ensure_ascii=True).replace("</", "<\\/")
    return f"""
    const glossary = {glossary_json};

    function toggleDeveloperDrawer() {{
      const drawer = document.getElementById("developer-drawer");
      const button = drawer.querySelector(".developer-toggle");
      const isOpen = drawer.classList.toggle("is-open");
      button.setAttribute("aria-expanded", String(isOpen));
    }}

    function closeTermPopover() {{
      const popover = document.getElementById("term-popover");
      popover.hidden = true;
      popover.innerHTML = "";
    }}

    function showTermPopover(trigger) {{
      const key = trigger.dataset.term;
      const item = glossary[key];
      if (!item) return;
      const popover = document.getElementById("term-popover");
      popover.innerHTML = `<h3>${{item.term}}</h3><p>${{item.definition}} ${{item.context}}</p>`;
      const box = trigger.getBoundingClientRect();
      const left = Math.min(box.left, window.innerWidth - 380);
      popover.style.left = `${{Math.max(16, left)}}px`;
      popover.style.top = `${{Math.min(window.innerHeight - 120, box.bottom + 10)}}px`;
      popover.hidden = false;
    }}

    document.querySelectorAll(".term-trigger").forEach((trigger) => {{
      trigger.addEventListener("mouseenter", () => showTermPopover(trigger));
      trigger.addEventListener("focus", () => showTermPopover(trigger));
      trigger.addEventListener("click", (event) => {{
        event.preventDefault();
        showTermPopover(trigger);
      }});
    }});

    document.addEventListener("keydown", (event) => {{
      if (event.key === "Escape") closeTermPopover();
    }});

    document.addEventListener("click", (event) => {{
      const target = event.target;
      if (!(target instanceof Element)) return;
      if (!target.closest(".term-trigger") && !target.closest("#term-popover")) {{
        closeTermPopover();
      }}
    }});
    """


def slugify(value: str) -> str:
    parts = []
    previous_dash = False
    for char in value.lower():
        if char.isalnum():
            parts.append(char)
            previous_dash = False
        elif not previous_dash:
            parts.append("-")
            previous_dash = True
    return "".join(parts).strip("-") or "analysis"


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
