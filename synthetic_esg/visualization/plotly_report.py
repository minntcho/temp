from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import plotly.graph_objects as go
from plotly.offline.offline import get_plotlyjs
from plotly.io import to_html


REPORT_COLORWAY = ["#0f766e", "#2563eb", "#b45309", "#6d28d9", "#b42318", "#64748b"]

FIGURE_METADATA: dict[str, dict[str, str]] = {
    "활동량 분포": {
        "chart_type": "히스토그램",
        "purpose": "생성된 활동량 값이 어느 범위에 주로 모여 있는지 보여줍니다.",
        "why": "생성 값이 자연스러운 범위에 모여 있는지, 특정 구간에 비정상적으로 몰려 있지는 않은지 확인하기 위해 실행합니다.",
        "read": "막대가 높을수록 해당 범위에 레코드가 많다는 뜻입니다. 오른쪽 꼬리가 길거나 외딴 막대가 보이면 유난히 큰 생성 값이 있다는 신호일 수 있습니다.",
        "check": "가장 오른쪽 값들이 지나치게 떨어져 보이면 다음 차트에서 활동 유형, 사업장 유형, 기간과 함께 비교해 보세요.",
    },
    "활동량 상자 그림": {
        "chart_type": "상자 그림",
        "purpose": "활동 유형별 일반적인 범위와 이상치를 비교합니다.",
        "why": "특정 활동 유형의 값이 다른 유형보다 훨씬 넓거나 작거나 극단적인지 보기 위해 실행합니다.",
        "read": "상자는 보통 값들이 모여 있는 중간 범위를 나타냅니다. 수염 밖의 점은 더 자세히 확인할 필요가 있는 이상치입니다.",
        "check": "큰 이상치는 의도한 스트레스 데이터인지, 우연히 들어간 노이즈인지 판단하기 위해 원천 파일과 비교해 보세요.",
    },
    "사업장 유형별 분포": {
        "chart_type": "그룹 상자 그림",
        "purpose": "사업장 유형별 활동량 범위가 눈에 띄게 다른지 확인합니다.",
        "why": "공장, 창고 등 사업장 유형마다 서로 다르지만 납득 가능한 활동 패턴이 만들어졌는지 확인하기 위해 실행합니다.",
        "read": "각 사업장 유형 안의 상자들을 비교합니다. 일부 유형에서는 차이가 클 수 있지만, 극단적인 간격은 검토가 필요합니다.",
        "check": "한 사업장 유형이 패턴을 과도하게 좌우한다면, 그 패턴을 유효하다고 보기 전에 사업장 메타데이터와 원천 구성 비율을 확인하세요.",
    },
    "월별 활동량 추이": {
        "chart_type": "선 그래프",
        "purpose": "생성된 활동량 합계가 시간 흐름에 따라 자연스럽게 움직이는지 보여줍니다.",
        "why": "현실적이지 않은 생성 동작을 의심하게 만드는 급등, 급락, 평평한 구간을 찾기 위해 실행합니다.",
        "read": "각 선은 하나의 활동 유형입니다. 알려진 이유 없이 갑자기 움직이는 선보다 완만하게 변하는 선이 보통 더 신뢰하기 쉽습니다.",
        "check": "특정 선이 급격히 튀면 해당 기간의 주입된 이상 패턴과 원천 레코드 수를 함께 비교하세요.",
    },
}

GLOSSARY: dict[str, dict[str, str]] = {
    "distribution": {
        "term": "분포",
        "definition": "값들이 어떤 범위에 얼마나 퍼져 있는지를 뜻합니다.",
        "context": "이 리포트에서는 생성 값이 균형 있게 퍼졌는지, 한곳에 몰렸는지, 지나치게 극단적인지 판단하는 데 사용합니다.",
    },
    "outlier": {
        "term": "이상치",
        "definition": "대부분의 값보다 훨씬 크거나 작은 값을 뜻합니다.",
        "context": "이상치는 실제로 드문 사례일 수도 있고, 의도적으로 주입한 이상 패턴이거나 생성 데이터 검토가 필요하다는 신호일 수도 있습니다.",
    },
    "log-scale": {
        "term": "로그 축",
        "definition": "매우 큰 값의 범위를 압축해 작은 값과 큰 값을 함께 비교할 수 있게 하는 축입니다.",
        "context": "ESG 활동량은 값의 규모 차이가 크게 날 수 있어, 로그 축을 쓰면 차트를 더 읽기 쉬워집니다.",
    },
    "histogram": {
        "term": "히스토그램",
        "definition": "숫자 값을 여러 범위로 나누고 각 범위에 몇 개의 레코드가 들어가는지 세는 차트입니다.",
        "context": "생성된 활동량이 주로 어느 구간에 놓이는지 답해 줍니다.",
    },
    "box-plot": {
        "term": "상자 그림",
        "definition": "일반적인 범위, 퍼짐 정도, 이상치를 한눈에 비교하는 압축된 차트입니다.",
        "context": "모든 행을 직접 읽지 않아도 활동 유형별 차이를 비교할 수 있게 해 줍니다.",
    },
    "trend": {
        "term": "추이",
        "definition": "시간이 지나면서 값이 움직이는 패턴을 뜻합니다.",
        "context": "추이 차트는 월별 합계가 납득 가능한 방향으로 움직이는지 확인합니다.",
    },
    "activity-type": {
        "term": "활동 유형",
        "definition": "전기, 가스, 스팀, 경유처럼 측정 대상이 되는 ESG 활동의 종류입니다.",
        "context": "활동 유형을 비교하면 특정 생성 소스만 다른 방식으로 움직이는지 발견할 수 있습니다.",
    },
    "standardized-amount": {
        "term": "표준화된 활동량",
        "definition": "서로 다른 원천의 레코드를 비교할 수 있도록 공통 단위로 변환한 값입니다.",
        "context": "이 리포트는 표준화된 활동량을 기준으로 생성된 활동 레코드를 일관되게 비교합니다.",
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
        ("활동량 분포", activity_histogram(joined_rows)),
        ("활동량 상자 그림", activity_boxplot(joined_rows)),
        ("사업장 유형별 분포", site_type_boxplot(joined_rows)),
        ("월별 활동량 추이", monthly_trend(joined_rows)),
    ]

    html = render_dashboard(
        title="Synthetic ESG 데이터 분포 리포트",
        run_dir=run_dir,
        distribution_stats=report.get("distribution_stats", {}),
        record_counts=report.get("record_counts", {}),
        figures=figures,
        include_plotlyjs=include_plotlyjs,
    )
    out_path = out_dir / "distribution_dashboard.html"
    if include_plotlyjs == "directory":
        (out_dir / "plotly.min.js").write_text(get_plotlyjs(), encoding="utf-8")
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
        title="활동량 분포",
        xaxis_title="표준화된 활동량",
        yaxis_title="레코드 수",
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
        title="활동량 상자 그림",
        yaxis_title="표준화된 활동량",
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
        title="사업장 유형별 활동량 분포",
        xaxis_title="사업장 유형",
        yaxis_title="표준화된 활동량",
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
        title="월별 활동량 추이",
        xaxis_title="기간",
        yaxis_title="표준화된 활동량 합계",
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
<html lang=\"ko\">
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
            생성된 ESG 활동 데이터의 범위, 패턴, 추가 확인 지점을 함께 살펴보기 위한 분석 리포트입니다.
          </p>
        </div>
        <div class=\"summary-chips\" aria-label=\"리포트 요약\">
          <span>{len(figures)}개 분석</span>
          <span>{record_total}개 레코드</span>
          <span>{escape_html(run_dir.name or str(run_dir))}</span>
        </div>
      </header>

      <section class=\"guide-card\" aria-labelledby=\"guide-title\">
        <p class=\"eyebrow\">분석 읽기 가이드</p>
        <h2 id=\"guide-title\">이 리포트를 읽는 방법</h2>
        <div class=\"guide-grid\">
          <div>
            <h3>1. 차트의 질문부터 확인</h3>
            <p>각 카드는 Plotly 차트를 보여주기 전에 해당 분석을 왜 실행하는지 먼저 설명합니다.</p>
          </div>
          <div>
            <h3>2. 후속 확인 지점 읽기</h3>
            <p>후속 메모를 기준으로 어떤 원천, 사업장, 기간, 활동 유형을 다시 봐야 할지 결정합니다.</p>
          </div>
          <div>
            <h3>3. 필요한 용어 도움말 열기</h3>
            <p>점선 밑줄이 있는 용어는 호버, 클릭, 탭, 키보드 포커스로 설명을 열 수 있습니다.</p>
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
            "chart_type": "Plotly 차트",
            "purpose": "생성된 ESG 데이터 패턴을 보여줍니다.",
            "why": "생성 데이터 품질을 확인하기 위해 실행합니다.",
            "read": "주요 시각 패턴을 서로 비교하며 읽습니다.",
            "check": "패턴이 예상과 다르면 원천 파일을 함께 검토하세요.",
        },
    )
    section_id = slugify(heading)
    return f"""
      <section class=\"analysis-card\" id=\"{section_id}\" aria-labelledby=\"{section_id}-title\">
        <div class=\"analysis-heading\">
          <div>
            <p class=\"eyebrow\">분석 {index}</p>
            <h2 id=\"{section_id}-title\">{escape_html(heading)}</h2>
            <p class=\"analysis-purpose\">{escape_html(metadata["purpose"])}</p>
          </div>
          <span class=\"chart-type\">{escape_html(metadata["chart_type"])}</span>
        </div>
        <div class=\"analysis-notes\">
          <div class=\"note-block why-run-this\">
            <h3>왜 실행하나?</h3>
            <p>{escape_html(metadata["why"])}</p>
          </div>
          <div class=\"note-block how-to-read-this\">
            <h3>어떻게 읽나</h3>
            <p>{escape_html(metadata["read"])}</p>
          </div>
          <div class=\"note-block follow-up what-to-check-next\">
            <h3>다음에 무엇을 확인하나?</h3>
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
          <p class=\"eyebrow\">용어 도움말</p>
          <h2 id=\"glossary-title\">읽으면서 설명 열기</h2>
          <p>
            주요 용어는 호버, 클릭, 탭, 키보드 포커스로 바로 설명을 확인할 수 있습니다.
            {render_term_trigger("distribution")}, {render_term_trigger("outlier")},
            {render_term_trigger("log-scale")}부터 확인하면 전체 흐름을 읽기 쉽습니다.
          </p>
        </div>
        <div class=\"term-list\" aria-label=\"용어 목록\">{triggers}</div>
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
    <aside class=\"developer-drawer\" id=\"developer-drawer\" aria-label=\"개발자 정보\">
      <button
        class=\"developer-toggle\"
        type=\"button\"
        aria-controls=\"developer-drawer\"
        aria-expanded=\"false\"
        onclick=\"toggleDeveloperDrawer()\"
      >
        개발자 정보
      </button>
      <div class=\"developer-content\">
        <p class=\"eyebrow\">개발자 정보</p>
        <h2>생성 산출물</h2>
        <div class=\"developer-section\">
          <h3>실행 디렉터리</h3>
          <pre>{escape_html(str(run_dir))}</pre>
        </div>
        <div class=\"developer-section\">
          <h3>분포 통계</h3>
          {stats_table}
        </div>
        <div class=\"developer-section\">
          <h3>레코드 수</h3>
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
        return "<p>분포 통계를 찾을 수 없습니다.</p>"
    headers = ["activity_type", "count", "min", "mean", "p50", "p95", "p99", "max"]
    rows = []
    for activity_type, stats in sorted(distribution_stats.items()):
        rows.append([activity_type] + [stats.get(header, "") for header in headers[1:]])
    return render_table(headers, rows)


def render_record_counts(record_counts: dict[str, Any]) -> str:
    if not record_counts:
        return "<p>레코드 수를 찾을 수 없습니다.</p>"
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
