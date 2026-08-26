# Data

`tickets.json` (500 records) and `accounts.json` (50 records) are the
synthetic mock dataset provided for this assignment — see
[DATA_SCHEMA.md](../DATA_SCHEMA.md) at the repo root for full field
documentation.

Note: the `category` and `urgency` fields on tickets are largely
decorrelated from the actual ticket body content in this dataset (verified
across the full 500-record set — e.g. 0% of `Data Loss`-labeled tickets
mention data loss in the body). The triage pipeline and eval harness treat
ticket text as the source of truth and do not use these fields as
classification input or as eval ground truth.
