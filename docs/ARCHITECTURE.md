# Architecture

This document helps agents and maintainers orient themselves before changing
the synthetic ESG generator. It is intentionally high level.

## Safety Guardrails

The Mermaid diagrams in this document are an orientation map, not a frozen
design mandate. They should explain the current architecture without preventing
the architecture from changing when the code needs to evolve.

- Keep diagrams focused on stable responsibilities and data flow.
- Do not copy full schemas or output contracts into this document.
- Treat detailed behavior in code and tests as more authoritative than diagrams.
- If a diagram conflicts with code, tests, or README intent, the diagram is
  stale; report the mismatch and update or remove the stale part.
- Mark future ideas as proposed. Do not draw proposed architecture as if it
  already exists.
- Prefer deleting detail from a diagram over making it a second source of truth.

## Source Of Truth Map

```mermaid
flowchart LR
  Readme["README.md<br/>Purpose and non-goals"]
  Agents["AGENTS.md<br/>Agent workflow rules"]
  Architecture["docs/ARCHITECTURE.md<br/>Orientation map"]
  Contract["synthetic_esg/generators/scaffold.py<br/>Output contract"]
  Code["synthetic_esg/<br/>Runtime behavior"]
  Tests["tests/<br/>Verification"]

  Readme --> Architecture
  Agents --> Architecture
  Architecture -.-> Code
  Contract --> Tests
  Code --> Tests
```

Authority order for ambiguous changes:

1. User request for the current task.
2. Code contracts and tests.
3. README purpose and non-goals.
4. This architecture map.
5. Agent convenience notes.

## Generation Flow

```mermaid
flowchart TD
  CLI["python -m synthetic_esg generate"]
  Args["argparse arguments"]
  Profile["profiles/*.yaml"]
  Config["GenerationConfig.from_args"]
  Scaffold["create_phase2_output"]
  Factory["populate_output_rows"]
  Master["master/*.csv"]
  Raw["raw_sources/*"]
  Truth["truth/*.csv"]
  Manifest["manifest.json"]
  Report["generation_report.json"]

  CLI --> Args
  Args --> Config
  Profile --> Config
  Config --> Scaffold
  Scaffold --> Factory
  Factory --> Master
  Factory --> Raw
  Factory --> Truth
  Scaffold --> Manifest
  Scaffold --> Report
```

## Module Responsibility Map

```mermaid
flowchart TD
  Config["config.py<br/>Profile, preset, and CLI override merge"]
  ProfileParser["profile.py<br/>Simple profile parsing"]
  Scaffold["generators/scaffold.py<br/>Output layout, headers, manifest, report"]
  Factory["generators/full_factory.py<br/>Current row generation orchestration"]
  Distributions["distributions.py<br/>Activity distributions and summaries"]
  Naming["naming.py<br/>Synthetic names"]
  Exporters["exporters/<br/>Reusable writing helpers"]
  Tests["tests/<br/>CLI, contract, profile, and distribution checks"]

  Config --> ProfileParser
  Scaffold --> Factory
  Factory --> Distributions
  Factory --> Naming
  Factory --> Exporters
  Tests --> Scaffold
  Tests --> Factory
```

`full_factory.py` currently owns more orchestration than the package structure
suggests. If future work splits this file, keep this document descriptive:
update the map after the code changes, not before, and avoid inventing a target
architecture unless the user asks for one.

## Boundary

This repository is a synthetic data factory. It should generate raw source
data, master data, truth labels, manifests, and reports. It should not become a
normalization pipeline, analytics service, API server, or real company data
model unless the project purpose is explicitly changed first.
