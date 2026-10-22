# CSV Cleaner

A small command-line tool that profiles a CSV file and applies the cleaning
fixes you choose: filling missing values, dropping incomplete rows, and
removing exact duplicates. Every change is written to a plain-English report,
so you can show exactly what happened to the data.

Built with Python and pandas. Runs locally - no accounts, no services, nothing
leaves your machine.

## Why it exists

Real datasets arrive messy: missing values, duplicates, inconsistent types.
This tool started as a portfolio project to demonstrate practical
data-quality work: profiling a dataset, choosing sensible fixes, and - just as
importantly - keeping an honest record of every change instead of silently
mutating data.

## What it does

1. **Profiles** the file: row/column counts, per-column missing values, exact
   duplicate rows.
2. **Applies only the fixes you ask for:**
   - `--fill age=median` - fill missing values in a column (mean, median,
     mode, zero, or any literal value). Repeatable.
   - `--drop-missing` - drop rows containing any missing value.
   - `--dedupe` - remove exact duplicate rows (keeps the first; runs before
     fills so duplicates can't bias fill statistics).
3. **Writes** a cleaned CSV plus a report listing every change in order.

It cannot certify the data is now correct - filling and deduplicating are
judgment calls. That is why the report exists.

## Setup

```bash
pip install -r requirements.txt
```

Requires Python 3.9+ and pandas. Verified with a clean install in a fresh
virtual environment.

## Usage

```bash
# Profile only - changes nothing
python3 csv_cleaner.py sample_data.csv

# Clean: dedupe, then fill missing values
python3 csv_cleaner.py sample_data.csv --dedupe --fill age=median --fill city=Unknown

# Choose output names
python3 csv_cleaner.py sample_data.csv --drop-missing --out clean.csv --report report.txt
```

`sample_data.csv` is included so you can try it immediately - it is
deliberately messy (missing values and duplicate rows).

Use non-sensitive data only: nothing with health records, payment details,
government IDs or passwords.

## Tests

```bash
python3 test_csv_cleaner.py
```

Nine tests cover profiling, each fix, error handling (missing file, malformed
CSV, bad column, invalid strategy) and the guarantees that a profile-only run
changes nothing on disk and the tool never overwrites its own input.

## Project layout

- `csv_cleaner.py` - the tool
- `test_csv_cleaner.py` - test suite (9 tests)
- `sample_data.csv` - messy demo data
- `requirements.txt` - dependencies

## Roadmap

- Interactive preview grid (show affected rows before applying)
- Column type coercion (text to number/date) with the same recorded-changes
  approach
- Simple web interface (Streamlit)

## Scope and limitations

This is a small, single-purpose command-line tool built as a portfolio
project - not a production data pipeline. It handles one flat CSV at a time,
has no graphical interface, and its fixes are the ones you explicitly request
on the command line. It does not connect to databases or cloud storage, does
not schedule runs, and makes no attempt to detect fuzzy duplicates (e.g. same
person, different spelling). The cleaned output is only as sound as the
choices you make; the report file exists so those choices stay auditable.

*Author: Varun Suresh*
