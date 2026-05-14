# Experimental Profiles

`lges_large.yaml` and `lges_stress.yaml` are kept here as future scale targets.

They are intentionally excluded from the default test suite and `--scale` presets because the row-generating factory now produces full master, truth, raw source, and source-map rows. These profiles should be promoted only after the generator has a dedicated long-running performance path.
