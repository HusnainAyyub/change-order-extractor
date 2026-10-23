# Writeup: change order extraction

## Approach

I kept this simple on purpose. The pipeline reads the file as text, using pypdf when the input is a PDF, then looks for each field in `fields.py`. Most change orders label their fields, so the first pass looks for labels like "Amount:" or "Project:" and takes the value next to the label. If a label is missing, a second pass uses patterns, for example a money amount with a dollar sign, or a phrase like "4 more days on the schedule". Dates are parsed with datetime and rewritten in ISO format. Amounts accept a leading minus, brackets, or the word credit, and credits come out negative.

## Confidence

Confidence is based on how a value was found, not on the value itself. A labelled match scores 0.95. A pattern match scores 0.7. A weak guess, like pulling a description out of a sentence, scores 0.4. A missing field scores 0.0. This is rough, but it tells the reader which fields to check first.

## Validation

`validate.py` checks the result. A missing co_number or project_name is an error. A date that is not in ISO format, or an amount that is not numeric, is also an error. Every missing field adds a warning, and so does any field with confidence under 0.5. Sample 4 shows this working: it has no schedule impact, so that field is null with a warning, and the rest still passes.

## Failure modes

Scanned PDFs with no text layer return nothing, because there is no OCR step. Amounts written in words, like "five thousand dollars", are missed. Tables that split a value across lines can break the label matching. A file with two change orders in it gets treated as one document, and the first match wins. Dates like 03/04/2026 are read as month first, which is wrong for day-first documents. OCR text with errors inside the numbers themselves, like "1O,OOO", will not parse as an amount.

## What I would improve next

Add an OCR fallback for scanned PDFs, handle amounts written in words, and score confidence using more signals per field, for example whether the value also passes a format check. I would also collect more real change orders and turn them into test cases, because four samples is a small set to trust.
