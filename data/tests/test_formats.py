import json
from pathlib import Path

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


def test_law_names_file():
    raw = json.loads((ROOT / "data" / "law_names.json").read_text())
    for rec in raw["laws"]:
        assert {"current_name", "former_names", "short_names", "aliases"} <= rec.keys()
        assert all(isinstance(rec[k], list) for k in ("former_names", "short_names", "aliases"))
    # renamed law (legalinfo.mn lawId=16530780109311): the former name still resolves to it
    permit = next(r for r in raw["laws"] if r["current_name"] == "Зөвшөөрөл, мэдэгдлийн тухай хууль")
    assert "Зөвшөөрлийн тухай хууль" in permit["former_names"]


def _copy_samples(tmp_path):
    for p in SAMPLES.iterdir():
        (tmp_path / p.name).write_bytes(p.read_bytes())
    return tmp_path


def _edit_jsonl(path, fn):
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    rows = fn(rows)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))


def test_integrity_catches_orphans_and_wrong_flags(tmp_path):
    d = _copy_samples(tmp_path)

    def break_refs(rows):
        rows[0]["to_law_id"] = "no-such-law"
        missing = next(r for r in rows if r["target_missing"])
        missing["target_missing"] = False
        rows[2]["confidence"] = 0.9
        return rows

    _edit_jsonl(d / "refs.jsonl", break_refs)
    _edit_jsonl(d / "similar.jsonl", lambda rows: [{**rows[0], "b_article_id": "x:1"}] + rows[1:])
    problems = "\n".join(validate_dir(d))
    assert "no-such-law" in problems
    assert "target_missing=False but provision exists=False" in problems
    assert "confidence 1.0" in problems
    assert "orphan b_article_id x:1" in problems


def test_integrity_requires_sample_label(tmp_path):
    d = _copy_samples(tmp_path)

    def unlabel(rows):
        rows[0]["articles"][1]["text"] = "label removed"
        return rows

    _edit_jsonl(d / "laws.jsonl", unlabel)
    assert any("not labelled [ЖИШЭЭ]" in p for p in validate_dir(d))


def test_validate_script_exit_code(tmp_path):
    import subprocess
    import sys

    ok = subprocess.run([sys.executable, str(ROOT / "scripts" / "validate_data.py")], capture_output=True)
    assert ok.returncode == 0, ok.stdout
    bad = subprocess.run([sys.executable, str(ROOT / "scripts" / "validate_data.py"), str(tmp_path)], capture_output=True)
    assert bad.returncode == 1
