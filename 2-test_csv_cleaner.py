"""Tests for csv_cleaner.py - run with: python3 -m pytest test_csv_cleaner.py -q
(or plain python3 test_csv_cleaner.py)
"""
import subprocess
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
TOOL = HERE / "csv_cleaner.py"


def run_tool(tmp, *cli_args):
    return subprocess.run([sys.executable, str(TOOL), *cli_args],
                          capture_output=True, text=True, cwd=tmp)


def make_messy(tmp):
    p = Path(tmp) / "messy.csv"
    p.write_text(
        "name,age,city\n"
        "Amara,31,Birmingham\n"
        "Ben,,Leeds\n"
        "Chloe,27,\n"
        "Amara,31,Birmingham\n"
        "Dan,24,\n"
    )
    return p


def test_profile_only_changes_nothing(tmp_path):
    src = make_messy(tmp_path)
    before = src.read_text()
    r = run_tool(tmp_path, str(src))
    assert r.returncode == 0, r.stderr
    assert "Total missing cells: 3" in r.stdout
    assert "Exact duplicate rows: 1" in r.stdout
    assert src.read_text() == before  # input untouched
    assert not (tmp_path / "messy_cleaned.csv").exists()  # nothing written


def test_fill_median_and_dedupe(tmp_path):
    src = make_messy(tmp_path)
    r = run_tool(tmp_path, str(src), "--fill", "age=median", "--fill", "city=Unknown", "--dedupe")
    assert r.returncode == 0, r.stderr
    out = pd.read_csv(tmp_path / "messy_cleaned.csv")
    assert len(out) == 4  # one exact duplicate removed
    assert out.isna().sum().sum() == 0
    assert out.loc[out["name"] == "Ben", "age"].iloc[0] == 27  # median of 31,27,24
    assert set(out.loc[out["city"] == "Unknown", "name"]) == {"Chloe", "Dan"}
    report = (tmp_path / "messy_report.txt").read_text()
    assert "filled 1 missing value(s) using median" in report
    assert "Removed 1 exact duplicate row(s)" in report


def test_drop_missing(tmp_path):
    src = make_messy(tmp_path)
    r = run_tool(tmp_path, str(src), "--drop-missing")
    assert r.returncode == 0, r.stderr
    out = pd.read_csv(tmp_path / "messy_cleaned.csv")
    assert len(out) == 2  # only the two complete Amara rows remain


def test_literal_fill_and_custom_paths(tmp_path):
    src = make_messy(tmp_path)
    r = run_tool(tmp_path, str(src), "--fill", "city=NoCity", "--out", "o.csv", "--report", "r.txt")
    assert r.returncode == 0, r.stderr
    out = pd.read_csv(tmp_path / "o.csv")
    assert (out["city"] == "NoCity").sum() == 2
    assert "Input:" in (tmp_path / "r.txt").read_text()


def test_bad_column_errors_cleanly(tmp_path):
    src = make_messy(tmp_path)
    r = run_tool(tmp_path, str(src), "--fill", "nope=mean")
    assert r.returncode != 0
    assert "No such column: nope" in (r.stderr + r.stdout)


def test_missing_file_errors_cleanly(tmp_path):
    r = run_tool(tmp_path, "ghost.csv")
    assert r.returncode != 0
    assert "File not found" in (r.stderr + r.stdout)


def test_mean_on_text_column_fails_safely(tmp_path):
    src = make_messy(tmp_path)
    r = run_tool(tmp_path, str(src), "--fill", "city=mean")
    assert r.returncode != 0  # pandas raises; tool must not write output
    assert not (tmp_path / "messy_cleaned.csv").exists()


def test_refuses_to_overwrite_input(tmp_path):
    src = make_messy(tmp_path)
    r = run_tool(tmp_path, str(src), "--dedupe", "--out", str(src))
    assert r.returncode != 0
    assert "Refusing to overwrite the input file" in (r.stderr + r.stdout)
    assert src.read_text() == make_messy(tmp_path).read_text()  # untouched


def test_malformed_csv_fails_cleanly(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_bytes(b"a,b\n1,2\n3,4,5,6\n\xff\xfe broken")
    r = run_tool(tmp_path, str(bad), "--dedupe")
    assert r.returncode != 0
    assert not (tmp_path / "bad_cleaned.csv").exists()


if __name__ == "__main__":
    import tempfile, traceback
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        with tempfile.TemporaryDirectory() as d:
            try:
                t(Path(d))
                print(f"PASS {t.__name__}")
            except Exception:
                failed += 1
                print(f"FAIL {t.__name__}")
                traceback.print_exc()
    sys.exit(1 if failed else 0)
