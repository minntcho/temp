# Agent Instructions

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
