# Symptom alerts and runbooks

The local dashboard visualizes thresholds. These rules define actionable conditions; a production alert evaluator would poll the log aggregates. Slack channel `#day13-alerts` is the intended destination, not an active integration in this starter.

## Alert 1

- **Fast request SLO burn:** Critical; SLI below 99.5% with at least 20 requests for 5 minutes. Owner: Nguyễn Minh Đức; Slack `#day13-alerts`.
- **User impact:** Answers take longer than 3 seconds or fail.
- **Check:** (1) Open latency P95 and SLI for the five minute window. (2) Filter `response_sent` slow requests and `request_failed`, copy a correlation ID. (3) Locate the trace and compare retriever/generation durations.
- **Mitigation:** Restore the last healthy retrieval/LLM path, then verify P95 and SLI recover. Do not suppress the alert without checking affected requests.

## Alert 2

- **User visible error rate:** Critical; failed/received above 2%, at least 20 requests, sustained 5 minutes. Owner: Nguyễn Minh Đức; Slack `#day13-alerts`.
- **User impact:** Requests return HTTP 500 instead of an answer.
- **Check:** (1) Compare traffic and error rate. (2) Group `request_failed` by `error_type` and collect correlation IDs. (3) Inspect the failing observation and its parent trace.
- **Mitigation:** Roll back the change or recover the failing dependency; rerun the workload and confirm the error rate drops.

## Alert 3

- **Cost budget burn:** Warning; 24 hour cost above $2.50 sustained 10 minutes. Owner: Nguyễn Minh Đức; Slack `#day13-alerts`.
- **User impact:** Spend exceeds the configured daily guardrail; output token growth may precede degraded latency.
- **Check:** (1) Compare cost by minute against traffic. (2) Group high cost `response_sent` events by model and feature. (3) Inspect generation usage/cost for matching correlation IDs.
- **Mitigation:** Revert a prompt change or cap output tokens after identifying the cause, and watch cost per request.
