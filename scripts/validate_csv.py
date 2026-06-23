#!/usr/bin/env python3
"""
Validate a student-contributed CSV before ingesting into the Gradiator database.
Run this before ingest_data.py to catch issues early.

Usage:
  python scripts/validate_csv.py data/new_semester.csv
  python scripts/validate_csv.py data/student_contribution.csv --strict
"""
import argparse
import sys
import os
import pandas as pd

# Required columns for the grade data
REQUIRED_COLUMNS = ["Course", "course title", "Academic Year", "Semester", "Instructor"]
VALID_SEMESTERS = {"Odd", "Even", "Summer"}

# Expected grade columns (at minimum, some of these should be present)
EXPECTED_GRADE_COLUMNS = ["D+", "D", "C", "C+", "B", "B+", "A", "A*", "E", "F"]


def validate_csv(csv_path: str, strict: bool = False) -> bool:
    """
    Validate a CSV file for Gradiator ingestion.
    Returns True if valid, False if errors found.
    """
    errors = []
    warnings = []

    # --- 1. File existence ---
    if not os.path.exists(csv_path):
        print(f"❌ FATAL: File not found: {csv_path}")
        return False

    # --- 2. Load CSV ---
    try:
        df = pd.read_csv(csv_path, keep_default_na=True)
    except Exception as e:
        print(f"❌ FATAL: Could not read CSV: {e}")
        return False

    print(f"📄 File: {csv_path}")
    print(f"📊 Rows: {len(df)}, Columns: {len(df.columns)}")
    print()

    # --- 3. Required columns check ---
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        errors.append(f"Missing required columns: {missing_cols}")

    # --- 4. Grade columns check ---
    present_grade_cols = [col for col in EXPECTED_GRADE_COLUMNS if col in df.columns]
    if not present_grade_cols:
        errors.append("No grade columns found! Expected at least some of: " + str(EXPECTED_GRADE_COLUMNS))
    else:
        # Check for the D+ to S^ range that ingest_data.py expects
        if "D+" not in df.columns:
            errors.append("Column 'D+' is missing — ingest_data.py uses it as the start marker for grade columns.")
        if "S^" not in df.columns:
            warnings.append("Column 'S^' is missing — ingest_data.py uses it as the end marker for grade columns.")

    # --- 5. Data quality checks ---
    if "Course" in df.columns:
        empty_courses = df["Course"].isna().sum()
        if empty_courses > 0:
            warnings.append(f"{empty_courses} rows have empty 'Course' values (will be skipped)")

        # Check course code format (e.g., CS101A, MTH202A)
        if not df["Course"].dropna().empty:
            sample_codes = df["Course"].dropna().head(5).tolist()
            print(f"📚 Sample course codes: {sample_codes}")

    if "Academic Year" in df.columns:
        unique_years = df["Academic Year"].dropna().unique()
        print(f"📅 Academic Years: {sorted(unique_years)}")

        # Check format (should be like "2023-2024")
        for year in unique_years:
            year_str = str(year).strip()
            if "-" not in year_str:
                warnings.append(f"Academic year '{year_str}' doesn't follow 'YYYY-YYYY' format")

    if "Semester" in df.columns:
        unique_sems = set(df["Semester"].dropna().unique())
        print(f"📆 Semesters: {sorted(unique_sems)}")

        invalid_sems = unique_sems - VALID_SEMESTERS
        if invalid_sems:
            errors.append(f"Invalid semester values: {invalid_sems}. Expected: {VALID_SEMESTERS}")

    if "Instructor" in df.columns:
        empty_instructors = df["Instructor"].isna().sum()
        if empty_instructors > 0:
            warnings.append(f"{empty_instructors} rows have empty 'Instructor' (will default to 'Unknown Instructor')")

        unique_instructors = df["Instructor"].dropna().nunique()
        print(f"🧑‍🏫 Unique instructors: {unique_instructors}")

    # --- 6. Grade value checks ---
    for col in present_grade_cols:
        if col in df.columns:
            non_numeric = 0
            negative = 0
            for val in df[col].dropna():
                try:
                    num = float(val)
                    if num < 0:
                        negative += 1
                except (ValueError, TypeError):
                    if str(val).strip().upper() != "NA":
                        non_numeric += 1

            if non_numeric > 0:
                errors.append(f"Column '{col}' has {non_numeric} non-numeric values")
            if negative > 0:
                errors.append(f"Column '{col}' has {negative} negative values")

    # --- 7. Unique offerings count ---
    if all(col in df.columns for col in ["Course", "Academic Year", "Semester"]):
        unique_offerings = df.groupby(["Course", "Academic Year", "Semester"]).ngroups
        unique_courses = df["Course"].dropna().nunique()
        print(f"\n📦 Summary: {unique_courses} courses, {unique_offerings} unique offerings across {len(df)} rows")

    # --- 8. Report ---
    print()
    if errors:
        print("=" * 50)
        print("❌ ERRORS (must fix before ingestion):")
        for e in errors:
            print(f"  • {e}")

    if warnings:
        print("=" * 50)
        print("⚠️  WARNINGS (non-fatal but check these):")
        for w in warnings:
            print(f"  • {w}")

    if not errors and not warnings:
        print("✅ All checks passed! CSV is ready for ingestion.")
    elif not errors:
        print("\n✅ No critical errors. Warnings above are non-fatal.")

    if strict and (errors or warnings):
        print("\n❌ STRICT MODE: Failing due to warnings/errors.")
        return False

    return len(errors) == 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate a CSV file before Gradiator ingestion.")
    parser.add_argument("csv_path", help="Path to the CSV file to validate")
    parser.add_argument("--strict", action="store_true", help="Fail on warnings too (not just errors)")
    args = parser.parse_args()

    valid = validate_csv(args.csv_path, strict=args.strict)
    sys.exit(0 if valid else 1)
