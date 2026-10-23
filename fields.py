"""Field definitions and extraction logic for change orders.

Extraction is label first. Most change orders name their fields, so a
value sitting next to a label is trusted more than a value found by a
bare pattern in the text. Every extractor returns (value, tier), where
tier is "labelled", "pattern", "weak", or None when nothing was found.
validate.py turns tiers into numeric confidence scores.
"""

import re
from datetime import datetime

FIELDS = [
    "co_number",
    "project_name",
    "date_issued",
    "contractor",
    "client",
    "description",
    "amount_usd",
    "schedule_impact_days",
    "reason",
    "status",
]

# Lines that start with one of these words end a multi-line block value
# (used for description, which sometimes wraps onto the next line).
_LABEL_START = re.compile(
    r"^(change\s*order|project|date|contractor|client|owner|description|"
    r"scope|amount|total|t0tal|schedule|reason|status|justification)\b",
    re.IGNORECASE,
)

_DATE_TOKEN = (
    r"(\d{4}-\d{2}-\d{2}"
    r"|\d{1,2}/\d{1,2}/\d{4}"
    r"|[A-Za-z]{3,9} \d{1,2},? \d{4}"
    r"|\d{1,2} [A-Za-z]{3,9} \d{4})"
)

_DATE_FORMATS = [
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%B %d, %Y",
    "%b %d, %Y",
    "%B %d %Y",
    "%b %d %Y",
    "%d %B %Y",
    "%d %b %Y",
]


def _parse_date(raw):
    raw = raw.strip().strip(",")
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _line_after_label(text, label_pattern):
    """Return the rest of the line after a 'Label:' style match."""
    m = re.search(
        r"(?:" + label_pattern + r")\s*[:\-]\s*(.+)", text, re.IGNORECASE
    )
    if not m:
        return None
    return m.group(1).strip()


def _block_after_label(text, label_pattern):
    """Return a labelled value, following wrapped lines if needed."""
    m = re.search(
        r"(?:" + label_pattern + r")\s*[:\-]\s*", text, re.IGNORECASE
    )
    if not m:
        return None
    lines = text[m.end():].splitlines()
    parts = []
    if lines and lines[0].strip():
        parts.append(lines[0].strip())
    for line in lines[1:]:
        stripped = line.strip()
        if not stripped or _LABEL_START.match(stripped):
            break
        parts.append(stripped)
    return " ".join(parts).strip() or None


def _co_number(text):
    m = re.search(
        r"change\s*order\s*(?:no\.?|number|#)?\s*[:#]?\s*(CO[-\s]?\d+)",
        text,
        re.IGNORECASE,
    )
    tier = "labelled"
    if not m:
        m = re.search(r"\b(CO[-\s]?\d{2,})\b", text)
        tier = "pattern"
    if not m:
        return None, None
    raw = m.group(1).upper().replace(" ", "-")
    if raw.startswith("CO") and not raw.startswith("CO-"):
        raw = "CO-" + raw[2:]
    return raw, tier


def _project_name(text):
    value = _line_after_label(text, r"project(?:\s*name)?")
    if value is None:
        return None, None
    # Drop a closing bracket or full stop from in-sentence mentions.
    value = value.split(")")[0].strip().rstrip(".")
    return value or None, "labelled" if value else None


def _date_issued(text):
    m = re.search(
        r"(?:date\s*issued|issued|date)\s*[:\-]\s*" + _DATE_TOKEN,
        text,
        re.IGNORECASE,
    )
    tier = "labelled"
    if not m:
        m = re.search(r"dated\s+" + _DATE_TOKEN, text, re.IGNORECASE)
        tier = "labelled"
    if not m:
        m = re.search(_DATE_TOKEN, text)
        tier = "pattern"
    if not m:
        return None, None
    parsed = _parse_date(m.group(1))
    if parsed is None:
        return None, None
    return parsed, tier


def _contractor(text):
    value = _line_after_label(text, r"contractor|submitted\s*by")
    if value:
        return value.rstrip("."), "labelled"
    m = re.search(
        r"([A-Z][A-Za-z&' ]*?(?:Inc\.|LLC|Ltd\.|Corp\.))\s+is the contractor",
        text,
    )
    if m:
        return m.group(1).strip(), "pattern"
    m = re.search(r"contractor\s+is\s+([^.,]+)", text, re.IGNORECASE)
    if m:
        return m.group(1).strip(), "pattern"
    return None, None


def _client(text):
    value = _line_after_label(text, r"client|owner")
    if value:
        return value.rstrip("."), "labelled"
    m = re.search(r"([A-Z][A-Za-z][A-Za-z&' ]*?)\s+is\s+the\s+client", text)
    if m:
        return m.group(1).strip(), "pattern"
    return None, None


def _description(text):
    value = _block_after_label(
        text, r"description|scope(?:\s*of\s*work)?|work\s*description|details"
    )
    if value:
        return value, "labelled"
    m = re.search(r"needs to\s+([^.]+\.)", text, re.IGNORECASE)
    if m:
        return m.group(1).strip().rstrip("."), "weak"
    return None, None


_AMOUNT_TOKEN = re.compile(
    r"(?P<sign>-)?\s*(?P<lp>\()?\s*\$\s*(?P<num>\d[\d,]*\.\d{2})\s*(?P<rp>\))?"
)
_AMOUNT_TOKEN_NO_DOLLAR = re.compile(
    r"(?P<sign>-)?\s*(?P<lp>\()?\s*(?P<num>\d[\d,]*\.\d{2})\s*(?P<rp>\))?"
)
_AMOUNT_LABEL = re.compile(
    r"(change\s*order\s*amount|amount|total|t0tal)\b", re.IGNORECASE
)


def _amount_value(match, context):
    value = float(match.group("num").replace(",", ""))
    negative = bool(match.group("sign") or match.group("lp"))
    if "credit" in context.lower():
        negative = True
    return -abs(value) if negative else value


def _amount(text):
    for line in text.splitlines():
        if _AMOUNT_LABEL.search(line):
            m = _AMOUNT_TOKEN.search(line) or _AMOUNT_TOKEN_NO_DOLLAR.search(line)
            if m:
                return _amount_value(m, line), "labelled"
    m = _AMOUNT_TOKEN.search(text)
    if m:
        line = text[: m.start()].splitlines()
        context = line[-1] if line else ""
        return _amount_value(m, context + text[m.start():].splitlines()[0]), "pattern"
    return None, None


def _schedule_impact(text):
    rest = _line_after_label(text, r"schedule\s*impact|schedule\s*extension|time\s*extension")
    if rest is not None:
        if re.search(r"none|no\s+impact|n/?a", rest, re.IGNORECASE):
            return 0, "labelled"
        m = re.search(r"(\d+)", rest)
        if m:
            return int(m.group(1)), "labelled"
    patterns = [
        r"(\d+)\s*more\s*days?\s*on\s*the\s*schedule",
        r"(\d+)\s*days?\s*added\s*to\s*the\s*schedule",
        r"add\s*(?:another\s*)?(\d+)\s*days?\s*to\s*the\s*schedule",
        r"extension\s*of\s*(\d+)\s*days?",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return int(m.group(1)), "pattern"
    if re.search(r"no\s+(schedule\s+)?impact", text, re.IGNORECASE):
        return 0, "pattern"
    return None, None


def _reason(text):
    value = _block_after_label(
        text, r"reason(?:\s*for\s*(?:the\s*)?change)?|justification"
    )
    if value:
        return value.rstrip("."), "labelled"
    return None, None


def _status(text):
    m = re.search(
        r"status\s*[:\-]\s*(approved|pending|rejected)", text, re.IGNORECASE
    )
    if m:
        return m.group(1).capitalize(), "labelled"
    m = re.search(
        r"status\s+is\s+(?:still\s+)?(approved|pending|rejected)",
        text,
        re.IGNORECASE,
    )
    if m:
        return m.group(1).capitalize(), "pattern"
    m = re.search(r"\b(approved|pending|rejected)\b", text, re.IGNORECASE)
    if m:
        return m.group(1).capitalize(), "weak"
    return None, None


_EXTRACTORS = {
    "co_number": _co_number,
    "project_name": _project_name,
    "date_issued": _date_issued,
    "contractor": _contractor,
    "client": _client,
    "description": _description,
    "amount_usd": _amount,
    "schedule_impact_days": _schedule_impact,
    "reason": _reason,
    "status": _status,
}


def extract_fields(text):
    """Extract all fields. Returns (values, tiers) dicts keyed by field."""
    values = {}
    tiers = {}
    for name in FIELDS:
        value, tier = _EXTRACTORS[name](text)
        values[name] = value
        tiers[name] = tier
    return values, tiers
