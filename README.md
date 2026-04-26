# PipelinePulse

A production-style data engineering system for simulating batch pipelines, monitoring job health, detecting failures, and generating analytics-ready datasets.

Author: Maharshi Roy  
GitHub: https://github.com/MaharshiRoy  
Suggested repository: `pipelinepulse`

---

## 🎯 Overview

PipelinePulse models real-world batch data workflows by generating job runs, tracking failures, detecting SLA breaches, performing data quality checks, identifying recurring incident patterns, and producing analytics-ready datasets.

It is designed to emulate how modern data platforms monitor and maintain batch pipelines in production environments, with a focus on reliability, observability, and operational insights.

---

## 🏗️ Architecture

```mermaid
flowchart TD

A[Batch Job Generator] --> B[Processing Engine]

B --> C[(SQLite Database)]

C --> D[Batch Runs Table]
C --> E[Data Quality Checks Table]
C --> F[Incident Patterns Table]
C --> G[Daily Job Health Mart]

D --> H[CSV Exports]
E --> H
F --> H
G --> H

H --> I[Analytics / Dashboards]
