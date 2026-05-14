# Archived Consumer Examples

These scripts are kept as references for downstream consumers of generated ESG data.

They are not part of the generator's core scope. The main repository direction is generation-only:

- create master data
- create raw source data
- inject controlled noise
- emit ground truth labels
- write manifest and generation reports

## Files

- `process_esg_dummy_data.py`: example unit normalization and emissions calculation consumer
- `normalize_multisource_esg.py`: example raw-to-staging normalization consumer
- `esg_excel_skeleton.py`: example Excel-based preprocessing and estimation flow

Future generator work should not add processing, normalization, API, or analytics responsibilities back into the main package.
