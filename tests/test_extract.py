import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from extract import extract_file

SAMPLES = Path(__file__).resolve().parents[1] / "samples"


def test_sample_1_form():
    result = extract_file(SAMPLES / "sample_1.txt")
    f = result["fields"]
    assert f["co_number"] == "CO-101"
    assert f["project_name"].startswith("Riverside Tower")
    assert f["amount_usd"] == 18450.00
    assert f["date_issued"] == "2026-03-03"
    assert f["schedule_impact_days"] == 6
    assert f["status"] == "Approved"
    assert result["validation"]["valid"] is True


def test_sample_2_email():
    result = extract_file(SAMPLES / "sample_2.txt")
    f = result["fields"]
    assert f["co_number"] == "CO-077"
    assert f["amount_usd"] == 9875.50
    assert "Northgate" in f["project_name"]
    assert f["date_issued"] == "2026-04-14"
    assert f["schedule_impact_days"] == 4
    assert f["status"] == "Pending"


def test_sample_3_ocr():
    result = extract_file(SAMPLES / "sample_3.txt")
    f = result["fields"]
    assert f["co_number"] == "CO-209"
    assert f["amount_usd"] == 12750.00
    assert "Harborview Clinic" in f["project_name"]
    assert f["date_issued"] == "2026-04-18"
    assert f["schedule_impact_days"] == 3
    assert f["status"] == "Approved"


def test_sample_4_credit_and_missing_schedule():
    result = extract_file(SAMPLES / "sample_4.txt")
    f = result["fields"]
    assert f["co_number"] == "CO-315"
    assert f["amount_usd"] == -3200.00
    assert "Elm Street" in f["project_name"]
    assert f["status"] == "Pending"
    assert f["schedule_impact_days"] is None
    warnings = " ".join(result["validation"]["warnings"])
    assert "schedule_impact_days" in warnings
