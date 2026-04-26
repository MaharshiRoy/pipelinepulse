# Architecture

## System Goal

This project demonstrates data engineering reliability work: monitoring batch jobs, finding recurring failures, validating data quality, and producing marts for analytics.

## Pipeline Flow

```text
Job metadata
     |
     v
Synthetic batch run generation
     |
     v
Data quality checks
     |
     v
Recurring failure detection
     |
     v
Daily job health mart + CSV exports
```

## Important Tables

- `batch_jobs`
- `batch_runs`
- `data_quality_checks`
- `incident_patterns`
- `mart_daily_job_health`

## Reliability Metrics

- Total job runs
- Success rate
- Failed runs
- SLA breaches
- Quality check failures
- Recurring error codes
- Affected job count

## RCA Examples

| Error code | Recommendation |
| --- | --- |
| `SRC_TIMEOUT` | Add retry with exponential backoff and validate source availability window |
| `DUPLICATE_KEY` | Check upstream deduplication and enforce merge key uniqueness |
| `SCHEMA_DRIFT` | Add schema contract checks before transform execution |
| `ROW_COUNT_MISMATCH` | Compare source filters, late-arriving records, and watermark logic |
| `TARGET_LOCK` | Reduce transaction scope or move heavy transforms outside contention windows |

