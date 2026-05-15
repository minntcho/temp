# Explainable Plotly Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the generated Plotly report into a reader-first analysis guide with inline term help and a collapsed developer information drawer.

**Architecture:** Keep the existing Python-generated HTML report and iframe delivery path. Add report metadata, shared Plotly styling, analysis-card rendering, glossary popovers, and developer drawer HTML inside `synthetic_esg/visualization/plotly_report.py`.

**Tech Stack:** Python standard library, Plotly, existing `unittest` test suite, generated HTML/CSS/JavaScript.

---

### Task 1: Add Regression Tests For Reader-First Report Markup

**Files:**
- Modify: `tests/test_visualization.py`
- Test: `tests/test_visualization.py`

- [ ] **Step 1: Write the failing test**

Add assertions to `VisualizationTests.test_visualize_creates_plotly_dashboard`:

```python
self.assertIn("analysis-guide", html)
self.assertIn("why-run-this", html)
self.assertIn("how-to-read-this", html)
self.assertIn("what-to-check-next", html)
self.assertIn("term-trigger", html)
self.assertIn("developer-drawer", html)
self.assertIn("developer information", html)
self.assertNotIn("non-expert", html)
self.assertNotIn("beginner", html)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest tests.test_visualization.VisualizationTests.test_visualize_creates_plotly_dashboard -q
```

Expected: fail because current generated HTML does not contain the new analysis guide classes or developer drawer.

- [ ] **Step 3: Implement minimal report markup**

Update `synthetic_esg/visualization/plotly_report.py` to render:

- An analysis guide shell.
- One explanation card per existing figure.
- Glossary term buttons with class `term-trigger`.
- A collapsed `<aside class="developer-drawer">`.

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
python -m unittest tests.test_visualization.VisualizationTests.test_visualize_creates_plotly_dashboard -q
```

Expected: pass.

### Task 2: Add Plotly Template And Analysis Metadata

**Files:**
- Modify: `synthetic_esg/visualization/plotly_report.py`
- Test: `tests/test_visualization.py`

- [ ] **Step 1: Write the failing test**

Add assertions that generated HTML includes the human-facing labels:

```python
self.assertIn("analysis reading guide", html)
self.assertIn("activity amount histogram", html)
self.assertIn("activity amount box plot", html)
self.assertIn("site type distribution", html)
self.assertIn("monthly activity trend", html)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest tests.test_visualization.VisualizationTests.test_visualize_creates_plotly_dashboard -q
```

Expected: fail until report metadata is rendered.

- [ ] **Step 3: Implement metadata-driven cards**

Create a small metadata map keyed by the current figure headings. Each entry defines:

- chart type
- short purpose
- why-run-this text
- how-to-read-this text
- what-to-check-next text

Use that metadata in `render_dashboard` instead of rendering a bare section.

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
python -m unittest tests.test_visualization.VisualizationTests.test_visualize_creates_plotly_dashboard -q
```

Expected: pass.

### Task 3: Add Glossary And Drawer Interactions

**Files:**
- Modify: `synthetic_esg/visualization/plotly_report.py`
- Test: `tests/test_visualization.py`

- [ ] **Step 1: Write the failing test**

Add assertions that interaction hooks are present:

```python
self.assertIn("aria-expanded", html)
self.assertIn("data-term", html)
self.assertIn("toggleDeveloperDrawer", html)
self.assertIn("closeTermPopover", html)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest tests.test_visualization.VisualizationTests.test_visualize_creates_plotly_dashboard -q
```

Expected: fail until the JavaScript hooks are rendered.

- [ ] **Step 3: Implement lightweight JavaScript**

Add script functions:

```javascript
function toggleDeveloperDrawer() { ... }
function closeTermPopover() { ... }
```

Term triggers should respond to click and keyboard focus. The drawer control should toggle `aria-expanded`.

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
python -m unittest tests.test_visualization.VisualizationTests.test_visualize_creates_plotly_dashboard -q
```

Expected: pass.

### Task 4: Full Verification

**Files:**
- Verify: repository test suite

- [ ] **Step 1: Run visualization test**

```powershell
python -m unittest tests.test_visualization -q
```

Expected: pass.

- [ ] **Step 2: Run full Python test suite**

```powershell
python -m unittest discover -s tests -p "test_*.py" -q
```

Expected: pass.

- [ ] **Step 3: Generate a sample report**

```powershell
python -m synthetic_esg generate --profile profiles/lges_smoke.yaml --out-dir out/explainable_probe --meters 40 --seed 41
python -m synthetic_esg visualize --run-dir out/explainable_probe --plotly-js inline
```

Expected: `out/explainable_probe/reports/distribution_dashboard.html` exists and includes analysis cards, glossary triggers, and developer drawer markup.
