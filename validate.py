"""Validation and confidence scoring for extracted change order fields.

Confidence comes from how a value was found, not from the value itself:
a labelled match scores highest, a bare pattern match scores in the
middle, and a weak or ambiguous match scores low. Missing fields get
0.0 and a validation warning.
"""

import re

TIER_SCORES = {
    "labelled": 0.95,
    "pattern": 0.7,
    "weak": 0.4,
    None: 0.0,
}

REQUIRED = ("co_number", "project_name")
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def score_confidence(tier):
    return TIER_SCORES.get(tier, 0.0)


def validate(values, confidence):
    """Check extracted values. Returns {valid, errors, warnings}."""
    errors = []
    warnings = []

    for name in REQUIRED:
        if not values.get(name):
            errors.append(f"missing required field: {name}")

    amount = values.get("amount_usd")
    if amount is not None and not isinstance(amount, (int, float)):
        errors.append(f"amount_usd is not numeric: {amount!r}")

    date = values.get("date_issued")
    if date is not None and not ISO_DATE.match(str(date)):
        errors.append(f"date_issued is not a valid ISO date: {date}")

    for name, value in values.items():
        if value is None:
            warnings.append(f"missing field: {name}")
        elif confidence.get(name, 0.0) < 0.5:
            warnings.append(f"low confidence for {name}: {confidence[name]}")

    return {"valid": not errors, "errors": errors, "warnings": warnings}
