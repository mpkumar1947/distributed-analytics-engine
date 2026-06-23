import argparse
import asyncio
import os
import sys
import logging
from typing import Dict, Set

import pandas as pd
from dotenv import load_dotenv

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, selectinload
from sqlalchemy.dialects.postgresql import insert as pg_insert

# ------------------------------------------------------------------------------
# PATH SETUP (to import api models)
# ------------------------------------------------------------------------------
BASE_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)

from api import models  # noqa: E402

# ------------------------------------------------------------------------------
# LOGGING
# ------------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# ENV & CONFIG
# ------------------------------------------------------------------------------
load_dotenv(os.path.join(BASE_DIR, ".env"))

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    logger.error("DATABASE_URL not set in .env")
    sys.exit(1)

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# asyncpg expects 'ssl=require', not 'sslmode=require'
DATABASE_URL = DATABASE_URL.replace("sslmode=require", "ssl=require")

DEFAULT_CSV_PATH = os.path.join(BASE_DIR, "data", "courses_with_fileids.csv")

# ------------------------------------------------------------------------------
# DB SETUP
# ------------------------------------------------------------------------------
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionFactory = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# ------------------------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------------------------
def normalize_instructor_name(name) -> str:
    if pd.isna(name) or not str(name).strip():
        return "Unknown Instructor"
    return str(name).strip().title()


def safe_int(row: pd.Series, key: str) -> int:
    val = row.get(key)
    if pd.isna(val) or str(val).strip().upper() in {"NA", ""}:
        return 0
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return 0


# ------------------------------------------------------------------------------
# INGESTION LOGIC
# ------------------------------------------------------------------------------
async def ingest_data(csv_path: str, mode: str = "incremental") -> None:
    logger.info(f"Loading CSV: {csv_path}")
    logger.info(f"Ingestion mode: {mode.upper()}")
    df = pd.read_csv(csv_path, keep_default_na=True)

    # ---- Validate grade columns ----
    try:
        start_idx = df.columns.get_loc("D+")
        end_idx = df.columns.get_loc("S^")
        grade_columns = df.columns[start_idx : end_idx + 1]
    except KeyError as exc:
        logger.error(f"Required grade column missing: {exc}")
        return

    processed_count = 0
    new_offerings = 0
    updated_offerings = 0

    async with AsyncSessionFactory() as session:
        async with session.begin():
            # ---- FULL MODE: Wipe existing data first ----
            if mode == "full":
                logger.info("FULL MODE: Clearing existing grade & offering data...")
                await session.execute(delete(models.Grade))
                await session.execute(delete(models.offering_instructor_association))
                await session.execute(delete(models.Offering))
                logger.info("Existing data cleared.")
            else:
                logger.info("INCREMENTAL MODE: Upserting only — existing data preserved.")

            course_cache: Dict[str, models.Course] = {}
            instructor_cache: Dict[str, models.Instructor] = {}

            for _, row in df.iterrows():
                course_code = str(row.get("Course", "")).strip().upper()
                if not course_code:
                    continue

                # ------------------------------------------------------------------
                # COURSE UPSERT (same for both modes)
                # ------------------------------------------------------------------
                if course_code not in course_cache:
                    course_name = str(row.get("course title", "")).strip() or course_code

                    stmt = (
                        pg_insert(models.Course)
                        .values(code=course_code, name=course_name)
                        .on_conflict_do_update(
                            index_elements=["code"],
                            set_={"name": course_name}
                        )
                        .returning(models.Course)
                    )

                    course_cache[course_code] = (
                        await session.execute(stmt)
                    ).scalar_one()

                # ------------------------------------------------------------------
                # INSTRUCTORS UPSERT (same for both modes)
                # ------------------------------------------------------------------
                raw_instructors = str(row.get("Instructor", ""))
                instructor_names: Set[str] = {
                    normalize_instructor_name(n)
                    for n in raw_instructors.split(",")
                    if n.strip()
                } or {"Unknown Instructor"}

                current_instructors = []

                for name in sorted(instructor_names):
                    if name not in instructor_cache:
                        stmt = (
                            pg_insert(models.Instructor)
                            .values(name=name)
                            .on_conflict_do_update(
                                index_elements=["name"],
                                set_={"name": name}
                            )
                            .returning(models.Instructor)
                        )
                        instructor_cache[name] = (
                            await session.execute(stmt)
                        ).scalar_one()

                    current_instructors.append(instructor_cache[name])

                # ------------------------------------------------------------------
                # OFFERING UPSERT (key change for incremental mode)
                # ------------------------------------------------------------------
                offering_data = {
                    "course_code": course_code,
                    "academic_year": str(row["Academic Year"]).strip(),
                    "semester": str(row["Semester"]).strip(),
                    "total_registered": safe_int(row, "Total Registered"),
                    "current_registered": safe_int(row, "Current Registered"),
                    "total_drop": safe_int(row, "Total Drop"),
                    "accepted_drop": safe_int(row, "Accepted Drop"),
                    "plot_file_id": str(row.get("telegram_file_id", "")).strip() or None,
                }

                stmt = (
                    pg_insert(models.Offering)
                    .values(**offering_data)
                    .on_conflict_do_update(
                        index_elements=[
                            "course_code",
                            "academic_year",
                            "semester"
                        ],
                        set_={
                            k: v
                            for k, v in offering_data.items()
                            if k not in {"course_code", "academic_year", "semester"}
                        }
                    )
                    .returning(models.Offering.id)
                )

                offering_id = (await session.execute(stmt)).scalar_one()

                offering_obj = await session.get(
                    models.Offering,
                    offering_id,
                    options=[selectinload(models.Offering.instructors)]
                )

                if offering_obj:
                    offering_obj.instructors = current_instructors
                    session.add(offering_obj)

                # ------------------------------------------------------------------
                # GRADES UPSERT (update counts if conflict)
                # ------------------------------------------------------------------
                for grade_type in grade_columns:
                    count_val = safe_int(row, grade_type)
                    if count_val > 0:
                        grade_stmt = (
                            pg_insert(models.Grade)
                            .values(
                                offering_id=offering_id,
                                grade_type=grade_type.strip(),
                                count=count_val,
                            )
                            .on_conflict_do_update(
                                constraint="uq_grade",
                                set_={"count": count_val}
                            )
                        )
                        await session.execute(grade_stmt)

                processed_count += 1
                if processed_count % 100 == 0:
                    logger.info(f"Processed {processed_count} rows...")

    logger.info(f"Ingestion completed successfully ({mode.upper()} mode). Total rows: {processed_count}")


# ------------------------------------------------------------------------------
# ENTRY POINT
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Ingest grade data from CSV into the database.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # First-time setup (wipe all and re-insert):
  python scripts/ingest_data.py --mode full

  # New semester data (add/update without touching existing):
  python scripts/ingest_data.py --mode incremental

  # Student-contributed data from a different CSV:
  python scripts/ingest_data.py --csv data/even_2026.csv --mode incremental
        """
    )
    parser.add_argument(
        "--mode",
        choices=["full", "incremental"],
        default="incremental",
        help="'full' wipes existing data first. 'incremental' (default) upserts only."
    )
    parser.add_argument(
        "--csv",
        default=DEFAULT_CSV_PATH,
        help=f"Path to CSV file. Default: {DEFAULT_CSV_PATH}"
    )
    args = parser.parse_args()

    if not os.path.exists(args.csv):
        logger.error(f"CSV file not found: {args.csv}")
        sys.exit(1)

    asyncio.run(ingest_data(csv_path=args.csv, mode=args.mode))
