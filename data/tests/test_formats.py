import json
from pathlib import Path

from pipeline.ids import law_id
from pipeline.validate import validate_dir

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "contracts" / "fixtures" / "processed"


def test_contract_samples_are_valid():
    assert validate_dir(SAMPLES) == []


def test_real_processed_output_is_valid():
    assert validate_dir(ROOT / "data" / "processed") == []


def test_validator_catches_drift(tmp_path):
    line = json.loads((SAMPLES / "refs.jsonl").read_text().splitlines()[0])
    line["method"] = "guess"
    (tmp_path / "refs.jsonl").write_text(json.dumps(line, ensure_ascii=False) + "\n")
    assert validate_dir(tmp_path)


def test_law_names_map():
    names = json.loads((ROOT / "data" / "law_names.json").read_text())
    assert all(isinstance(v, list) for v in names.values())
    assert law_id("Зөвшөөрлийн тухай хууль") in {law_id(k) for k in names}
