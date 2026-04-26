-- Daily reliability trend
SELECT
    business_date,
    total_runs,
    successful_runs,
    failed_runs,
    sla_breaches,
    success_rate,
    avg_duration_seconds,
    total_rows_written
FROM mart_daily_job_health
ORDER BY business_date;

-- Top recurring failures
SELECT
    error_code,
    occurrences,
    affected_jobs,
    first_seen,
    last_seen,
    recommendation
FROM incident_patterns
ORDER BY occurrences DESC;

-- Failed critical jobs
SELECT
    runs.business_date,
    jobs.job_name,
    jobs.domain,
    jobs.criticality,
    runs.error_code,
    runs.error_message,
    runs.duration_seconds
FROM batch_runs AS runs
JOIN batch_jobs AS jobs
  ON jobs.job_id = runs.job_id
WHERE runs.status = 'FAILED'
  AND jobs.criticality IN ('high', 'critical')
ORDER BY runs.business_date DESC, jobs.criticality;

-- Failed data quality checks
SELECT
    checks.checked_at,
    runs.business_date,
    jobs.job_name,
    checks.check_name,
    checks.failed_records,
    checks.threshold_failed_records
FROM data_quality_checks AS checks
JOIN batch_runs AS runs
  ON runs.run_id = checks.run_id
JOIN batch_jobs AS jobs
  ON jobs.job_id = runs.job_id
WHERE checks.status = 'FAIL'
ORDER BY checks.checked_at DESC;

