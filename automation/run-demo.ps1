# Runs the recurring Prometheus demo job via Claude Code, unattended.
# Triggered twice a week by Windows Task Scheduler.
# Prompt is piped via stdin (not passed as a CLI argument) since it's long
# and may contain characters PowerShell would otherwise need escaped.

Set-Location "E:\Linkedin"

$logDir = "E:\Linkedin\automation\logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$logFile = Join-Path $logDir ("run-{0}.log" -f (Get-Date -Format "yyyy-MM-dd_HHmmss"))

Get-Content -Raw -Path "E:\Linkedin\automation\recurring-task-prompt.md" | claude -p --permission-mode dontAsk *> $logFile
