# Change Order Extractor

Small Python tool that pulls structured fields out of change orders. Input is a text file or a PDF with a text layer. Output is JSON with the extracted fields, a confidence score per field, and a validation result.

## Fields

| Field | Type | Notes |
| --- | --- | --- |
| co_number | string | Example: CO-101 |
| project_name | string | |
| date_issued | string | ISO format, YYYY-MM-DD |
| contractor | string | |
| client | string | |
| description | string | Short text of the work |
| amount_usd | number | Signed, credits are negative |
| schedule_impact_days | integer or null | Days added to the schedule |
| reason | string | Why the change was made |
| status | string | Approved, Pending, Rejected, or null |

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

The only runtime dependency is pypdf, and it is only needed for PDF input. pytest is used for the tests.

## Usage

```bash
python3 extract.py samples/sample_1.txt
python3 extract.py samples/sample_1.txt --out result.json
python3 extract.py some_change_order.pdf
```

Real output for `samples/sample_1.txt`:

```json
{
  "source_file": "sample_1.txt",
  "fields": {
    "co_number": "CO-101",
    "project_name": "Riverside Tower - Level 4 Fit Out",
    "date_issued": "2026-03-03",
    "contractor": "BuildRight Construction LLC",
    "client": "Harbor Group Properties",
    "description": "Add two glass partition walls in the open office area on level 4.",
    "amount_usd": 18450.0,
    "schedule_impact_days": 6,
    "reason": "Client requested additional meeting rooms",
    "status": "Approved"
  },
  "confidence": {
    "co_number": 0.95,
    "project_name": 0.95,
    "date_issued": 0.95,
    "contractor": 0.95,
    "client": 0.95,
    "description": 0.95,
    "amount_usd": 0.95,
    "schedule_impact_days": 0.95,
    "reason": 0.95,
    "status": 0.95
  },
  "validation": {
    "valid": true,
    "errors": [],
    "warnings": []
  }
}
```

PDF input takes the same path once pypdf has read the text layer. I tested with a PDF copy of sample_1 and got the same 10 fields out.

## Confidence scores

Confidence is based on how a value was found, not on the value itself.

- Labelled match, the value sits next to a label like "Amount:": 0.95
- Pattern match, the value was found by a pattern with no clear label: 0.7
- Weak match, a best guess pulled out of a sentence: 0.4
- Missing: 0.0, and validation adds a warning for the field

## Validation

`validate.py` checks the extracted values after extraction.

- Errors: missing co_number, missing project_name, an amount that is not numeric, a date that is not in ISO format.
- Warnings: any missing field, and any field with confidence under 0.5.

The result is valid only when there are no errors. Warnings do not fail validation, they mark what a person should check.

## Tests

```bash
python3 -m pytest tests/
```

The tests run the extractor on all four samples and check the key fields. Result from my run: 4 passed.

## Results on the samples

| Sample | Style | Fields filled | Notes |
| --- | --- | --- | --- |
| sample_1.txt | Tidy form | 10 of 10 | Valid, no warnings |
| sample_2.txt | Email thread | 10 of 10 | Description scored 0.4, flagged as low confidence |
| sample_3.txt | Noisy OCR style | 10 of 10 | Valid, no warnings |
| sample_4.txt | Edge case, credit | 9 of 10 | schedule_impact_days missing and flagged with a warning, amount came out as -3200.0 |

## Files

- `extract.py` - CLI entry point, reads the file, prints or writes the JSON
- `fields.py` - Field definitions and the extraction logic
- `validate.py` - Validation checks and confidence scoring
- `samples/` - Four sample change orders in different layouts
- `tests/` - pytest tests over the samples
- `writeup.md` - Short writeup of the approach and failure modes
