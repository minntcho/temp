# Agent Instructions

## Architecture Notes

Read `docs/ARCHITECTURE.md` before making broad structural changes.
That document uses Mermaid diagrams as an orientation map, not as a frozen
design mandate.

- Do not add nested `AGENTS.md` files unless the user explicitly asks.
- Do not duplicate the repository purpose or output contract in agent notes.
- The project purpose and non-goals live in `README.md`.
- The output contract lives in `synthetic_esg/generators/scaffold.py`.
- If architecture notes conflict with code, tests, or the README, treat the
  notes as stale and report the mismatch before changing behavior.

## Setup

Install the repository dependencies before running the generator or test suite.
The test suite imports `faker` through `synthetic_esg.naming`, so a clean agent
environment will fail with `ModuleNotFoundError: No module named 'faker'` unless
dependencies are installed first.

```powershell
python -m pip install -r requirements.txt
```

For a minimal test-only setup, installing Faker is sufficient:

```powershell
python -m pip install "Faker>=25,<26"
```

## Tests

The tests are written with the Python standard library `unittest` framework.
Use this command as the default verification step:

```powershell
python -m unittest discover -s tests -p "test_*.py" -q
```

Do not assume `pytest` is installed in the agent environment.
