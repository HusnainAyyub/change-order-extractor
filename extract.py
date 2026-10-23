#!/usr/bin/env python3
"""CLI entry point for the change order extractor.

Usage:
    python3 extract.py <file.txt|file.pdf> [--out result.json]

Reads a change order as plain text, or extracts the text layer from a
PDF with pypdf, and prints validated JSON with confidence scores.
"""

import argparse
import json
import sys
from pathlib import Path

import fields as fields_mod
import validate as validate_mod


def read_text(path):
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return path.read_text(encoding="utf-8", errors="replace")


def extract_file(path):
    text = read_text(path)
    values, tiers = fields_mod.extract_fields(text)
    confidence = {
        name: validate_mod.score_confidence(tiers.get(name))
        for name in fields_mod.FIELDS
    }
    validation = validate_mod.validate(values, confidence)
    return {
        "source_file": Path(path).name,
        "fields": values,
        "confidence": confidence,
        "validation": validation,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Extract structured fields from a change order."
    )
    parser.add_argument("file", help="Path to a .txt or .pdf change order")
    parser.add_argument(
        "--out", help="Optional path to also write the JSON result to"
    )
    args = parser.parse_args(argv)

    try:
        result = extract_file(args.file)
    except FileNotFoundError:
        print(f"error: file not found: {args.file}", file=sys.stderr)
        return 1
    except ImportError:
        print(
            "error: reading PDFs needs pypdf, run: pip install -r requirements.txt",
            file=sys.stderr,
        )
        return 1

    text = json.dumps(result, indent=2)
    print(text)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
