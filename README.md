# cronwrap

Lightweight wrapper for cron jobs that adds logging, alerting, and retry logic.

## Installation

```bash
pip install cronwrap
```

## Usage

Wrap any shell command or script with `cronwrap` to get automatic logging, failure alerts, and retries on error.

**Basic example:**

```bash
cronwrap --retries 3 --alert email@example.com -- python /path/to/job.py
```

**Python API:**

```python
from cronwrap import CronJob

job = CronJob(
    command="python /path/to/job.py",
    retries=3,
    alert="email@example.com",
    log_file="/var/log/cronwrap/job.log"
)

job.run()
```

**Configuration via `cronwrap.yml`:**

```yaml
jobs:
  daily_report:
    command: python /scripts/report.py
    retries: 3
    alert: ops@example.com
    timeout: 300
    log_file: /var/log/cronwrap/report.log
```

Then in your crontab:

```
0 8 * * * cronwrap run daily_report
```

## Features

- **Logging** — captures stdout/stderr with timestamps to a log file
- **Alerting** — sends email or webhook notifications on failure
- **Retries** — automatically retries failed jobs with configurable backoff
- **Timeouts** — kills jobs that exceed a specified duration

## Requirements

- Python 3.8+

## License

MIT © cronwrap contributors