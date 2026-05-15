# Explainable Plotly Report Design

## Context

The repository currently generates synthetic ESG data and a Plotly HTML
distribution report. The web dashboard embeds that report inside a run detail
page, but the report itself assumes that readers already know what each
analysis means.

The new report experience should help readers understand the purpose and
interpretation of each analysis before exposing implementation details.

## Goals

- Make the Plotly report readable as an analysis guide, not only as chart
  output.
- Explain why each chart exists, how to read it, and what follow-up question it
  answers.
- Keep developer-oriented artifacts available without showing them by default.
- Provide inline explanations for specialized terms without labeling readers by
  expertise level.

## Non-Goals

- Replacing Plotly with another charting library.
- Building a full analytics product or normalization pipeline.
- Moving raw manifests, file trees, or command output into the default reading
  path.
- Hiding developer artifacts entirely.

## Audience And Tone

The default page should speak to someone trying to understand the generated ESG
data and the role of each analysis. It should avoid labels that classify the
reader by expertise level because those labels can feel patronizing.

Use neutral labels such as:

- Analysis guide
- How to read this
- Why this matters
- Follow-up check
- Developer information

## Page Structure

The report uses a reader-first layout with a collapsed developer drawer.

Default visible content:

- Report title and short purpose statement.
- Run summary chips such as profile, seed, row count, and report status.
- Analysis cards for each Plotly figure.
- Inline term help for specialized concepts.
- Follow-up guidance when a chart suggests possible anomalies or data quality
  concerns.

Secondary content:

- A right-side collapsed developer drawer.
- Manifest JSON.
- Run file tree.
- Visual report path.
- Generation and visualization commands.
- Raw execution metadata.

## Analysis Card Pattern

Each chart should be wrapped in an explanation card with the same structure:

1. Chart name and chart type.
2. One-sentence purpose.
3. "Why run this?" explanation.
4. "How to read this?" explanation.
5. "What should I check next?" follow-up.
6. The Plotly chart.
7. Optional warning or insight callout when generated data suggests a notable
   pattern.

The first set of cards should cover the existing figures:

- Activity amount histogram: shows where generated activity amounts are
  concentrated and whether extreme values appear.
- Activity amount box plot: compares typical ranges and outliers by activity
  type.
- Site type distribution: checks whether site categories show noticeably
  different activity ranges.
- Monthly activity trend: checks whether generated amounts move plausibly over
  time.

## Term Help

Specialized terms should be marked inline with a subtle dotted underline and an
accessible trigger.

Interaction requirements:

- Hover opens the term explanation on desktop.
- Click or tap pins the same explanation.
- Keyboard focus opens the same explanation.
- Escape or outside click closes pinned explanations.

Each term explanation should include:

- Plain-language definition.
- Why the term matters in this report.
- How to interpret it in the current chart.

Initial glossary terms:

- Distribution
- Outlier
- Log scale
- Histogram
- Box plot
- Trend
- Activity type
- Standardized amount

## Developer Drawer

The developer drawer should be discoverable but visually secondary. It can
appear as a narrow right rail labeled "Developer information" or "Dev details".

When opened, it should show technical artifacts in compact tabs or sections:

- Manifest
- Run files
- Execution metadata
- Commands

The drawer should not change the analysis card layout unless the viewport is
too narrow, in which case it can open as an overlay panel.

## Visual Style

Match the existing dashboard tokens and operational tone:

- Background: light green-gray.
- Surface: white panels with 8px radius.
- Accent: teal for guidance and navigation.
- Amber/red for caution and follow-up checks.
- Compact, readable cards rather than marketing-style sections.
- Plotly charts should use a restrained multi-color palette for activity
  categories, not only teal.

## Data Flow

The report continues to be generated from the existing Python visualization
module. The enhanced report can remain an HTML artifact served through the
current Next.js iframe route.

Recommended path:

1. Add shared report metadata for each Plotly figure.
2. Apply a common Plotly template matching the web dashboard style.
3. Render analysis cards and glossary data into the generated HTML.
4. Add lightweight JavaScript for glossary popovers and the developer drawer.
5. Keep the existing API route for serving the generated report.

## Accessibility

- Term help must work without hover.
- Drawer controls must be reachable by keyboard.
- Popovers should be dismissible and not block chart interaction.
- Button labels should describe actions directly.
- Color should not be the only signal for warnings or status.

## Testing

Testing should cover:

- Existing visualization test still verifies report generation.
- Generated HTML includes the report title, analysis card labels, and glossary
  triggers.
- Developer drawer content is present but not shown in the default reading
  path.
- The report remains embeddable in the current run detail iframe.

Manual verification should include:

- Opening a generated report in the Next.js run detail page.
- Checking desktop and narrow viewport layouts.
- Confirming glossary help works by hover, click, tap-like interaction, and
  keyboard focus.
- Confirming the developer drawer opens and closes without hiding the chart
  explanation flow.
