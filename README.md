# PipelinePulse

Data engineering portfolio project for Data Engineer and Software Engineer roles.

Author: Maharshi Roy  
GitHub: https://github.com/MaharshiRoy  
Suggested repository: `pipelinepulse`

This project simulates a production batch monitoring platform. It generates batch job runs, tracks failures, detects SLA breaches, runs data quality checks, identifies recurring failure patterns, and exports analyst-ready marts.

## Why This Project Is Resume-Worthy

- Matches real production support and data engineering work.
- Demonstrates batch monitoring, RCA support, and data quality validation.
- Uses SQL-friendly tables instead of only printing logs.
- Produces CSV outputs that can feed dashboards.
- Runs with Python standard libraries only.

## Tech Stack

- Python
- SQLite
- SQL
- CSV exports

## Run Locally

```powershell
python src/pipelinepulse.py --db artifacts/service_ops_demo.sqlite --days 21 --seed 42 --export-dir artifacts/exports
```

Outputs:

```text
artifacts/service_ops_demo.sqlite
artifacts/exports/batch_jobs.csv
artifacts/exports/batch_runs.csv
artifacts/exports/data_quality_checks.csv
artifacts/exports/incident_patterns.csv
artifacts/exports/mart_daily_job_health.csv
```

## What It Simulates

- 10 recurring batch jobs
- 21 days of job runs by default
- Success and failure states
- SLA breach detection
- Row count metrics
- Data quality checks
- Recurring incident pattern detection
- Daily job health mart

## Data Model

| Table | Purpose |
| --- | --- |
| `batch_jobs` | Job metadata such as domain, owner, SLA, and criticality |
| `batch_runs` | Run-level status, duration, row counts, and error details |
| `data_quality_checks` | Check-level pass/fail results |
| `incident_patterns` | Repeated error patterns and recommendations |
| `mart_daily_job_health` | Daily reliability mart for dashboarding |

## Resume Bullets

- Developed a Python and SQLite ETL monitoring platform that simulates batch jobs, SLA breaches, data quality checks, and recurring incident patterns.
- Built SQL-friendly monitoring marts and CSV exports for job health reporting and RCA analysis.
- Implemented failure pattern recommendations for common production issues such as source timeouts, schema drift, duplicate keys, and row count mismatches.

## GitHub Publish

Create a public GitHub repository named `pipelinepulse`, then run:

```powershell
git remote add origin https://github.com/MaharshiRoy/pipelinepulse.git
git push -u origin main
```
