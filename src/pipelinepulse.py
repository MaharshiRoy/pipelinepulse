from __future__ import annotations

import argparse
import csv
import random
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path


@dataclass(frozen=True)
class JobSpec:
    job_id: str
    job_name: str
    domain: str
    owner_team: str
    sla_minutes: int
    schedule_cron: str
    criticality: str


JOBS = [
    JobSpec("job_customer_extract", "Customer Extract", "booking", "data-platform", 20, "0 1 * * *", "high"),
    JobSpec("job_provider_extract", "Provider Extract", "booking", "data-platform", 20, "5 1 * * *", "high"),
    JobSpec("job_service_catalog", "Service Catalog Load", "booking", "data-platform", 25, "15 1 * * *", "medium"),
    JobSpec("job_booking_fact", "Booking Fact Build", "warehouse", "analytics-eng", 35, "0 2 * * *", "high"),
    JobSpec("job_payment_fact", "Payment Fact Build", "warehouse", "analytics-eng", 30, "20 2 * * *", "high"),
    JobSpec("job_provider_scores", "Provider Score Refresh", "analytics", "analytics-eng", 40, "0 3 * * *", "medium"),
    JobSpec("job_customer_retention", "Customer Retention Mart", "analytics", "analytics-eng", 45, "30 3 * * *", "medium"),
    JobSpec("job_ops_kpi", "Operations KPI Mart", "analytics", "analytics-eng", 30, "0 4 * * *", "high"),
    JobSpec("job_quality_snapshot", "Data Quality Snapshot", "quality", "data-quality", 25, "30 4 * * *", "high"),
    JobSpec("job_alert_dispatch", "Alert Dispatch", "quality", "data-quality", 15, "45 4 * * *", "critical"),
]


ERRORS = [
    ("SRC_TIMEOUT", "Source system timed out during extraction."),
    ("DUPLICATE_KEY", "Duplicate primary key detected in staging table."),
    ("SCHEMA_DRIFT", "Unexpected column or type change detected."),
    ("ROW_COUNT_MISMATCH", "Source and target row counts are outside tolerance."),
    ("TARGET_LOCK", "Warehouse target table lock exceeded retry window."),
]


QUALITY_CHECKS = [
    "primary_key_not_null",
    "primary_key_unique",
    "accepted_status_values",
    "source_to_target_row_count",
    "foreign_key_relationships",
]


RECOMMENDATIONS = {
    "SRC_TIMEOUT": "Add retry with exponential backoff and validate source availability window.",
    "DUPLICATE_KEY": "Check upstream deduplication and enforce merge key uniqueness before load.",
    "SCHEMA_DRIFT": "Add schema contract checks before transform execution.",
    "ROW_COUNT_MISMATCH": "Compare source filters, late-arriving records, and incremental watermark logic.",
    "TARGET_LOCK": "Move heavy transforms outside the contention window or reduce transaction scope.",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate an ETL monitoring demo database.")
    parser.add_argument("--db", default="artifacts/service_ops_demo.sqlite", help="SQLite output database path.")
    parser.add_argument("--days", type=int, default=21, help="Number of business days to simulate.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for repeatable output.")
    parser.add_argument("--export-dir", default="artifacts/exports", help="Directory for CSV exports.")
    return parser.parse_args()


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS batch_jobs (
            job_id TEXT PRIMARY KEY,
            job_name TEXT NOT NULL,
            domain TEXT NOT NULL,
            owner_team TEXT NOT NULL,
            sla_minutes INTEGER NOT NULL,
            schedule_cron TEXT NOT NULL,
            criticality TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS batch_runs (
            run_id TEXT PRIMARY KEY,
            job_id TEXT NOT NULL REFERENCES batch_jobs(job_id),
            business_date TEXT NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT NOT NULL,
            status TEXT NOT NULL,
            duration_seconds INTEGER NOT NULL,
            rows_read INTEGER NOT NULL,
            rows_written INTEGER NOT NULL,
            error_code TEXT,
            error_message TEXT
        );

        CREATE TABLE IF NOT EXISTS data_quality_checks (
            check_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL REFERENCES batch_runs(run_id),
            check_name TEXT NOT NULL,
            status TEXT NOT NULL,
            failed_records INTEGER NOT NULL,
            threshold_failed_records INTEGER NOT NULL,
            checked_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS incident_patterns (
            error_code TEXT PRIMARY KEY,
            occurrences INTEGER NOT NULL,
            affected_jobs INTEGER NOT NULL,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            recommendation TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS mart_daily_job_health (
            business_date TEXT PRIMARY KEY,
            total_runs INTEGER NOT NULL,
            successful_runs INTEGER NOT NULL,
            failed_runs INTEGER NOT NULL,
            sla_breaches INTEGER NOT NULL,
            success_rate REAL NOT NULL,
            avg_duration_seconds REAL NOT NULL,
            total_rows_written INTEGER NOT NULL
        );
        """
    )


def reset_data(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DELETE FROM data_quality_checks;
        DELETE FROM incident_patterns;
        DELETE FROM mart_daily_job_health;
        DELETE FROM batch_runs;
        DELETE FROM batch_jobs;
        """
    )


def seed_jobs(conn: sqlite3.Connection) -> None:
    conn.executemany(
        """
        INSERT INTO batch_jobs (
            job_id,
            job_name,
            domain,
            owner_team,
            sla_minutes,
            schedule_cron,
            criticality
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                job.job_id,
                job.job_name,
                job.domain,
                job.owner_team,
                job.sla_minutes,
                job.schedule_cron,
                job.criticality,
            )
            for job in JOBS
        ],
    )


def generate_runs(conn: sqlite3.Connection, days: int, seed: int) -> None:
    rng = random.Random(seed)
    today = date.today()
    start_day = today - timedelta(days=days - 1)

    for day_index in range(days):
        business_date = start_day + timedelta(days=day_index)

        for job_index, job in enumerate(JOBS):
            start_at = datetime.combine(
                business_date,
                time(hour=1 + (job_index // 3), minute=(job_index * 7) % 60),
                tzinfo=timezone.utc,
            )

            fail_probability = 0.08
            if job.criticality == "critical":
                fail_probability = 0.11
            elif job.criticality == "high":
                fail_probability = 0.09

            has_periodic_source_issue = business_date.day % 9 == 0 and job.domain in {"booking", "warehouse"}
            failed = rng.random() < fail_probability or has_periodic_source_issue

            duration_multiplier = rng.uniform(0.55, 1.35)
            if failed:
                duration_multiplier = rng.uniform(0.15, 0.95)
            elif rng.random() < 0.12:
                duration_multiplier = rng.uniform(1.1, 1.8)

            duration_seconds = max(60, int(job.sla_minutes * 60 * duration_multiplier))
            completed_at = start_at + timedelta(seconds=duration_seconds)

            rows_read = rng.randint(5_000, 250_000)
            rows_written = 0 if failed else int(rows_read * rng.uniform(0.93, 1.0))
            error_code = None
            error_message = None

            if failed:
                error_code, error_message = rng.choice(ERRORS)
                if has_periodic_source_issue:
                    error_code = "SRC_TIMEOUT"
                    error_message = RECOMMENDATIONS[error_code]

            run_id = f"{business_date:%Y%m%d}_{job.job_id}"

            conn.execute(
                """
                INSERT INTO batch_runs (
                    run_id,
                    job_id,
                    business_date,
                    started_at,
                    completed_at,
                    status,
                    duration_seconds,
                    rows_read,
                    rows_written,
                    error_code,
                    error_message
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    job.job_id,
                    business_date.isoformat(),
                    start_at.isoformat(),
                    completed_at.isoformat(),
                    "FAILED" if failed else "SUCCESS",
                    duration_seconds,
                    rows_read,
                    rows_written,
                    error_code,
                    error_message,
                ),
            )


def run_quality_checks(conn: sqlite3.Connection, seed: int) -> None:
    rng = random.Random(seed + 1000)
    rows = conn.execute("SELECT run_id, status, completed_at FROM batch_runs ORDER BY run_id").fetchall()

    for row in rows:
        if row["status"] == "FAILED":
            conn.execute(
                """
                INSERT INTO data_quality_checks (
                    check_id,
                    run_id,
                    check_name,
                    status,
                    failed_records,
                    threshold_failed_records,
                    checked_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"{row['run_id']}_pipeline_completed",
                    row["run_id"],
                    "pipeline_completed",
                    "FAIL",
                    1,
                    0,
                    row["completed_at"],
                ),
            )
            continue

        for check_name in QUALITY_CHECKS:
            threshold = 0 if check_name != "source_to_target_row_count" else 50
            failed_records = 0

            if rng.random() < 0.045:
                failed_records = rng.randint(1, 120)

            status = "PASS" if failed_records <= threshold else "FAIL"

            conn.execute(
                """
                INSERT INTO data_quality_checks (
                    check_id,
                    run_id,
                    check_name,
                    status,
                    failed_records,
                    threshold_failed_records,
                    checked_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"{row['run_id']}_{check_name}",
                    row["run_id"],
                    check_name,
                    status,
                    failed_records,
                    threshold,
                    row["completed_at"],
                ),
            )


def detect_incident_patterns(conn: sqlite3.Connection) -> None:
    failures = conn.execute(
        """
        SELECT
            error_code,
            COUNT(*) AS occurrences,
            COUNT(DISTINCT job_id) AS affected_jobs,
            MIN(started_at) AS first_seen,
            MAX(started_at) AS last_seen
        FROM batch_runs
        WHERE status = 'FAILED'
          AND error_code IS NOT NULL
        GROUP BY error_code
        HAVING COUNT(*) >= 2
        ORDER BY occurrences DESC
        """
    ).fetchall()

    conn.executemany(
        """
        INSERT INTO incident_patterns (
            error_code,
            occurrences,
            affected_jobs,
            first_seen,
            last_seen,
            recommendation
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row["error_code"],
                row["occurrences"],
                row["affected_jobs"],
                row["first_seen"],
                row["last_seen"],
                RECOMMENDATIONS.get(row["error_code"], "Review job logs and upstream dependencies."),
            )
            for row in failures
        ],
    )


def refresh_marts(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        INSERT INTO mart_daily_job_health (
            business_date,
            total_runs,
            successful_runs,
            failed_runs,
            sla_breaches,
            success_rate,
            avg_duration_seconds,
            total_rows_written
        )
        SELECT
            runs.business_date,
            COUNT(*) AS total_runs,
            SUM(CASE WHEN runs.status = 'SUCCESS' THEN 1 ELSE 0 END) AS successful_runs,
            SUM(CASE WHEN runs.status = 'FAILED' THEN 1 ELSE 0 END) AS failed_runs,
            SUM(CASE WHEN runs.duration_seconds > jobs.sla_minutes * 60 THEN 1 ELSE 0 END) AS sla_breaches,
            ROUND(SUM(CASE WHEN runs.status = 'SUCCESS' THEN 1.0 ELSE 0.0 END) * 100.0 / COUNT(*), 2) AS success_rate,
            ROUND(AVG(runs.duration_seconds), 2) AS avg_duration_seconds,
            SUM(runs.rows_written) AS total_rows_written
        FROM batch_runs AS runs
        JOIN batch_jobs AS jobs
          ON jobs.job_id = runs.job_id
        GROUP BY runs.business_date
        ORDER BY runs.business_date
        """
    )


def export_csv(conn: sqlite3.Connection, export_dir: Path) -> None:
    export_dir.mkdir(parents=True, exist_ok=True)
    tables = [
        "batch_jobs",
        "batch_runs",
        "data_quality_checks",
        "incident_patterns",
        "mart_daily_job_health",
    ]

    for table in tables:
        rows = conn.execute(f"SELECT * FROM {table}").fetchall()
        if not rows:
            continue

        output_path = export_dir / f"{table}.csv"
        with output_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(dict(row) for row in rows)


def print_summary(conn: sqlite3.Connection, db_path: Path, export_dir: Path) -> None:
    summary = conn.execute(
        """
        SELECT
            COUNT(*) AS total_runs,
            SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) AS successful_runs,
            SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) AS failed_runs,
            ROUND(SUM(CASE WHEN status = 'SUCCESS' THEN 1.0 ELSE 0.0 END) * 100.0 / COUNT(*), 2) AS success_rate
        FROM batch_runs
        """
    ).fetchone()

    sla_breaches = conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM batch_runs AS runs
        JOIN batch_jobs AS jobs
          ON jobs.job_id = runs.job_id
        WHERE runs.duration_seconds > jobs.sla_minutes * 60
        """
    ).fetchone()["count"]

    quality_failures = conn.execute(
        "SELECT COUNT(*) AS count FROM data_quality_checks WHERE status = 'FAIL'"
    ).fetchone()["count"]

    patterns = conn.execute(
        """
        SELECT error_code, occurrences, affected_jobs, recommendation
        FROM incident_patterns
        ORDER BY occurrences DESC
        LIMIT 3
        """
    ).fetchall()

    print("ETL Monitoring Demo Complete")
    print(f"Database: {db_path}")
    print(f"CSV exports: {export_dir}")
    print(f"Total runs: {summary['total_runs']}")
    print(f"Success rate: {summary['success_rate']}%")
    print(f"Failed runs: {summary['failed_runs']}")
    print(f"SLA breaches: {sla_breaches}")
    print(f"Quality check failures: {quality_failures}")

    if patterns:
        print("Top recurring failure patterns:")
        for row in patterns:
            print(
                f"- {row['error_code']}: {row['occurrences']} occurrences across "
                f"{row['affected_jobs']} jobs. {row['recommendation']}"
            )


def main() -> int:
    args = parse_args()
    if args.days < 1:
        raise ValueError("--days must be greater than zero")

    db_path = Path(args.db)
    export_dir = Path(args.export_dir)

    with connect(db_path) as conn:
        create_schema(conn)
        reset_data(conn)
        seed_jobs(conn)
        generate_runs(conn, args.days, args.seed)
        run_quality_checks(conn, args.seed)
        detect_incident_patterns(conn)
        refresh_marts(conn)
        conn.commit()
        export_csv(conn, export_dir)
        print_summary(conn, db_path, export_dir)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

