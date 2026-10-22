"""csv_cleaner.py - CSV Cleaner v1: profile and clean a CSV.

What it does:
  1. Profiles the file: row/column counts, per-column missing values and types,
     exact duplicate rows.
  2. Applies the fixes YOU choose (it never silently changes data):
       --drop-missing          drop rows that have any missing value
       --fill COL=STRATEGY     fill missing values in COL; strategy is:
                               mean | median | mode | zero | a literal value
                               (repeatable, e.g. --fill age=median --fill city=Unknown)
       --dedupe                remove exact duplicate rows (keeps the first)
  3. Writes a cleaned CSV and a plain-English report of every change.

It cannot certify the data is now correct - filling and deduping are judgment
calls. That is why every change is recorded in the report.

Usage:
  python3 csv_cleaner.py data.csv                      # profile only, no changes
  python3 csv_cleaner.py data.csv --dedupe --fill age=median
  python3 csv_cleaner.py data.csv --drop-missing --out clean.csv --report report.txt

Requires: python3 and pandas (pip install pandas). Runs locally; no accounts.
"""

import argparse
import sys
from pathlib import Path

import pandas as pd


def profile(df, out=print):
    rows, cols = df.shape
    out(f"Rows: {rows}   Columns: {cols}")
    total_missing = int(df.isna().sum().sum())
    dup_rows = int(df.duplicated().sum())
    for col in df.columns:
        missing = int(df[col].isna().sum())
        if missing:
            pct = missing / rows * 100 if rows else 0.0
            out(f"  missing: {col} - {missing} ({pct:.1f}%)")
    out(f"Total missing cells: {total_missing}")
    out(f"Exact duplicate rows: {dup_rows}")
    return total_missing, dup_rows


def fill_column(df, col, strategy, changes):
    if col not in df.columns:
        raise SystemExit(f"No such column: {col}. Columns are: {', '.join(map(str, df.columns))}")
    n_missing = int(df[col].isna().sum())
    if n_missing == 0:
        changes.append(f"{col}: no missing values, nothing filled.")
        return df
    if strategy == "mean":
        value = df[col].mean()
    elif strategy == "median":
        value = df[col].median()
    elif strategy == "mode":
        mode = df[col].mode(dropna=True)
        value = mode.iloc[0] if len(mode) else None
    elif strategy == "zero":
        value = 0
    else:
        value = strategy  # literal value
    if value is None or (isinstance(value, float) and pd.isna(value)):
        raise SystemExit(f"Cannot use strategy '{strategy}' on column '{col}' (no non-missing values to derive it from).")
    df[col] = df[col].fillna(value)
    changes.append(f"{col}: filled {n_missing} missing value(s) using {strategy} (value: {value}).")
    return df


def clean(df, args, changes):
    # Order matters: dedupe first so duplicates cannot bias fill statistics.
    if args.dedupe:
        before = len(df)
        df = df.drop_duplicates().copy()
        changes.append(f"Removed {before - len(df)} exact duplicate row(s), kept the first occurrence.")
    if args.drop_missing:
        before = len(df)
        df = df.dropna().copy()
        changes.append(f"Dropped {before - len(df)} row(s) containing missing values.")
    for spec in args.fill or []:
        if "=" not in spec:
            raise SystemExit(f"--fill expects COL=STRATEGY, got: {spec}")
        col, strategy = spec.split("=", 1)
        df = fill_column(df, col.strip(), strategy.strip(), changes)
    return df


def main(argv=None):
    p = argparse.ArgumentParser(description="Profile and clean a CSV file. All changes are recorded in a report.")
    p.add_argument("csv", help="input CSV file")
    p.add_argument("--drop-missing", action="store_true", help="drop rows with any missing value")
    p.add_argument("--fill", action="append", metavar="COL=STRATEGY",
                   help="fill missing values in COL (mean|median|mode|zero|literal). Repeatable.")
    p.add_argument("--dedupe", action="store_true", help="remove exact duplicate rows")
    p.add_argument("--out", help="cleaned CSV output path (default: <name>_cleaned.csv)")
    p.add_argument("--report", help="change report path (default: <name>_report.txt)")
    args = p.parse_args(argv)

    src = Path(args.csv)
    if not src.exists():
        raise SystemExit(f"File not found: {src}")
    try:
        df = pd.read_csv(src)
    except pd.errors.EmptyDataError:
        raise SystemExit(f"That file has no data in it: {src}")
    except pd.errors.ParserError as e:
        raise SystemExit(f"Could not parse {src} as a CSV: {e}")

    print(f"File: {src}")
    print("Before:")
    profile(df, lambda line: print("  " + line))

    changes = []
    fixing = args.drop_missing or args.fill or args.dedupe
    if fixing:
        df = clean(df, args, changes)

    if not changes:
        print("\nNo fixes requested - nothing changed. Re-run with --drop-missing, --fill or --dedupe.")
        print("Tip: every fix you choose is recorded in the report file.")
        return 0

    out_path = Path(args.out) if args.out else src.with_name(src.stem + "_cleaned.csv")
    report_path = Path(args.report) if args.report else src.with_name(src.stem + "_report.txt")
    # Non-destructive by design: never overwrite the input file.
    for target in (out_path, report_path):
        if target.resolve() == src.resolve():
            raise SystemExit(f"Refusing to overwrite the input file: {src}. Choose a different --out/--report name.")
    df.to_csv(out_path, index=False)

    print("\nAfter:")
    profile(df, lambda line: print("  " + line))
    print("\nChanges applied:")
    for c in changes:
        print(f"  - {c}")

    lines = [
        f"CSV Cleaner report",
        f"Input:  {src} ({len(pd.read_csv(src))} rows)",
        f"Output: {out_path} ({len(df)} rows)",
        "",
        "Changes applied, in order:",
    ] + [f"{i+1}. {c}" for i, c in enumerate(changes)] + [
        "",
        "Note: filling and deduplicating are judgment calls. This tool records",
        "what it changed; it cannot certify the data is now correct.",
    ]
    report_path.write_text("\n".join(lines) + "\n")
    print(f"\nWrote: {out_path}")
    print(f"Wrote: {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
