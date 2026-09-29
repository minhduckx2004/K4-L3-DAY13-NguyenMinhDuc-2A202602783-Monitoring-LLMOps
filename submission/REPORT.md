# Báo cáo cá nhân — K4-L3A Day 13 Monitoring & LLMOps

## 1. Thông tin

- **Họ tên:** Nguyễn Minh Đức
- **MSSV:** 2A202602783 · **Lớp:** K4-L3A
- **Repository:** https://github.com/minhduckx2004/K4-L3-DAY13-NguyenMinhDuc-2A202602783-Monitoring-LLMOps
- **Commit SHA nộp:** xem SHA của commit cuối được nộp cùng URL repository trên LMS/Codelabs.
- **Langfuse project cá nhân:** `day13-k4-l3a-2A202602783`
- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1` · **Cohort:** K4

## 2. Kết quả và evidence

| Hạng mục | Kết quả | Evidence |
|---|---|---|
| Tests cuối | 23 passed trong 1.72 s | [15-final-checks.png](evidence/15-final-checks.png) |
| Log validator cuối | 100/100; 117 records; 57 correlation IDs; 0 PII leaks | [15-final-checks.png](evidence/15-final-checks.png) |
| Dashboard validator | 6/6 panel | [15-final-checks.png](evidence/15-final-checks.png) |
| Structured log, PII | context đầy đủ, PII synthetic đã scrub | [04-structured-log.txt](evidence/04-structured-log.txt), [05-pii-redaction.txt](evidence/05-pii-redaction.txt) |
| Traces project cá nhân | ≥10 traces workload đầu tiên | [06-trace-list.png](evidence/06-trace-list.png) |
| Child observations | root, retrieval, generation; usage/cost | [07-trace-waterfall.png](evidence/07-trace-waterfall.png), [08a-trace-metadata.png](evidence/08a-trace-metadata.png), [08b-generation-usage.png](evidence/08b-generation-usage.png) |
| Prompt versions | v1 baseline, v2 candidate; promote v2 và rollback v1 | [09-prompt-versions.png](evidence/09-prompt-versions.png), [10a-production-v2.png](evidence/10a-production-v2.png), [10b-rollback-v1.png](evidence/10b-rollback-v1.png) |
| Dashboard runtime | sáu panel, 60 phút, refresh 30 giây | [11-dashboard-overview.png](evidence/11-dashboard-overview.png) |
| Challenge K4 | P95 2652 ms; một request 2652 ms; retriever 2.50 s | [12-incident-metric.png](evidence/12-incident-metric.png), [13-incident-log.png](evidence/13-incident-log.png), [14-incident-trace.png](evidence/14-incident-trace.png) |

**Evidence rollback:** [ảnh 10b](evidence/10b-rollback-v1.png) xác nhận sau rollback v1 có `production` và `baseline`, v2 giữ `candidate`; trace rollback đã ghi nhận ở bảng dưới.

## 3. Structured logging và PII

Middleware clear contextvars cho từng request, nhận `x-request-id` hợp lệ theo mẫu `req-<8-hex>` hoặc sinh UUID rút gọn, bind `correlation_id` và trả hai response headers `x-request-id`, `x-response-time-ms`. Trước `request_received`, ứng dụng bind user ID đã hash (SHA-256 rút gọn), session, feature, model và env. Processor scrub đệ quy các chuỗi trong event trước JSONL writer và JSON renderer; pattern gồm email, điện thoại VN, CCCD và thẻ. Kiểm tra cuối trên 117 records không phát hiện PII nguyên văn. Log, trace và report chỉ dùng dữ liệu thử.

## 4. Tracing và prompt versioning

`lab-agent-run` là observation gốc; `retriever` và `fake-llm` là child observations. Generation ghi model, input/output tokens, cost và TTFT metadata. Decorator tắt capture raw input/output, trong khi metadata truyền user hash, session, feature/model/env và `correlation_id` để nối trace với log. Ảnh generation cho thấy prompt liên kết và token/cost, ảnh metadata cho thấy `prompt_source=langfuse`.

| Lượt | Label | Version | Trace ID | Correlation ID / trạng thái |
|---|---|---:|---|---|
| Baseline | `baseline` | 1 | `154480d3b4fa186a5b2ff3a08b7ecd39` | `req-30804138`; Langfuse, không có fetch error |
| Candidate | `candidate` | 2 | `9f3c5fad2f2ef733c97678978d1aed12` | `req-d25dd55f`; cùng input “How should alerts be designed?” |
| Promote | `production` | 2 | `e4d6fd348c037e8b286a9a7e3b15ea38` | v2 có production trên ảnh 10a; Trace ID do học viên cung cấp |
| Rollback | `production` | 1 | `5a995b313e9933c8c5bc0f7bb95301a3` | ảnh 10b xác nhận production trở về v1 |

v1 dùng các biến `{{feature}}`, `{{docs}}`, `{{message}}`; v2 thêm chỉ dẫn trả lời tối đa ba bullet và giữ ba biến. Nhờ label, chuyển production sang v2 và rollback về v1 không cần sửa source. Restart API giữa các lượt để tránh cache prompt cũ.

## 5. Dashboard, SLO và alerts

Dashboard từ [config/dashboard.yaml](../config/dashboard.yaml) đọc `data/logs.jsonl` trong 60 phút, refresh 30 giây. Sáu panel lần lượt hiển thị (1) latency P50/P95/P99 và TTFT P95; (2) traffic; (3) error rate/breakdown và retrieval success; (4) cost; (5) tokens input/output; (6) quality proxy. Ảnh challenge có 55 requests trong cửa sổ, P50 151 ms, P95 2652 ms, P99 2665 ms, TTFT P95 50 ms, error rate 0%, retrieval success 100%, tổng cost $0.111555, 2125 input và 7012 output tokens, quality proxy 0.876. Đây là số liệu toàn cửa sổ, không chỉ năm request challenge.

[Primary SLO](../config/slo.yaml): 99.5% requests có `response_sent` trong ≤3000 ms trên cửa sổ 28 ngày. Error budget 0.5% số requests: 10,000 requests cho phép tối đa 50 requests chậm/lỗi. Ảnh challenge cho thấy 55/55 đạt, SLI 100%, budget còn 0.275 request; P95 tăng nhưng **chưa vi phạm ngưỡng 3000 ms**. Ba alert symptom-based trong [config/alert_rules.yaml](../config/alert_rules.yaml) theo dõi SLO burn, tỷ lệ lỗi và chi phí, kèm severity, duration, owner, Slack channel dự kiến và [runbook](../docs/alerts.md). Starter chỉ có cấu hình rule, chưa có evaluator/scheduler hoặc kết nối Slack thực sự. Quality proxy là heuristic, không thay thế đánh giá của người dùng.

## 6. Điều tra challenge chính thức

- **Challenge:** `day13-k4-l3a-monitoring-llmops-v1`; `python scripts/inject_incident.py` bật `rag_slow=True`, các incident khác false.
- **Metrics và khoảng thời gian:** khoảng 22:17 ngày 29/09/2026 (Asia/Ho_Chi_Minh). Dashboard P95 2652 ms, tăng từ P95 1083 ms trên ảnh trước challenge (khoảng 2.45 lần). Năm request challenge đều HTTP 200; client đo 5.33–13.30 giây khi concurrency 5, gồm cả thời gian chờ. Trong agent, `latency_ms` của request chọn là 2652 ms. Error rate 0%, retrieval success 100%.
- **Logs:** `req-68d097ac` có `request_received` lúc `2026-09-29T15:17:18.802428Z` và `response_sent` lúc `15:17:21.455217Z`; `latency_ms=2652`, `ttft_ms=50`, `tool_name=retrieval`, `tool_success=true`, `cost_usd=0.002115`. [Ảnh log](evidence/13-incident-log.png).
- **Trace cùng request:** ID `c3e319b2d842156fdc54742171bd9986`; metadata `correlation_id=req-68d097ac`, feature `monitoring`, prompt `day13-chat` production v1. Timeline cho thấy root **2.65 s**, `retriever` **2.50 s**, generation khoảng **152 ms**. [Ảnh trace](evidence/14-incident-trace.png).
- **Root cause:** challenge kích hoạt delay trong retrieval (`rag_slow`). Span retriever chiếm khoảng 94% thời lượng root; generation và TTFT ổn định. Request thành công nhưng chậm, vì vậy error rate không phản ánh sự cố.
- **Fix action:** tắt incident bằng `python scripts/inject_incident.py --scenario rag_slow --disable`; [ảnh kiểm tra cuối](evidence/15-final-checks.png) thấy `rag_slow=False`. Trong hệ thống thực, khôi phục hoặc tối ưu dependency retrieval, sau đó chạy cùng workload và xác minh P95 hạ.
- **Preventive measure:** theo dõi riêng duration retrieval theo feature, đặt timeout/caching và alert symptom-based cho P95 hoặc tốc độ tiêu thụ error budget, kiểm tra waterfall trước khi quy lỗi cho LLM.

## 7. Giải thích và tự đánh giá

Metrics xác định triệu chứng và khung giờ; log chọn một request bằng `correlation_id`; trace chỉ ra child gây trễ. Prompt versions cho phép thử v2 và rollback v1; tokens/cost nhận diện chi phí bất thường dù request vẫn thành công. Quyết định kỹ thuật là scrub tại processor trước writer để cả payload lồng nhau và error detail đi qua cùng điểm bảo vệ.

Một blocker trên Windows là terminal đầu tiên dùng Python hệ thống nên thiếu `structlog`/`langfuse`; kích hoạt `.venv` và chạy lại đạt 23 passed. Baseline validator trước khi sửa TODO không được đo nên không gán số. Số P95 dashboard khác thời gian client vì một bên đo trong agent, bên kia bao gồm chờ khi gửi đồng thời. Chưa có bằng chứng cấu hình Slack phát alert tự động; file YAML/runbook chỉ là thiết kế. Ảnh 10a và 10b thể hiện hai trạng thái label khác nhau trước và sau rollback.

## 8. Checklist trước nộp

- [x] Challenge K4 đúng ID; metric → log → trace cùng `req-68d097ac`.
- [x] Log validator 100/100, dashboard 6/6, pytest 23 passed trên lần chạy cuối.
- [x] Trace/prompt của project cá nhân, không chụp secret.
- [x] Ảnh rollback `10b-rollback-v1.png` cho thấy v1 `baseline` + `production`, v2 `candidate`.
- [ ] Kiểm tra bốn Trace IDs và đường dẫn ảnh trong repo; nộp commit SHA cuối trên LMS/Codelabs.
- [ ] Không commit `.env`, `config/challenge.json`, `.venv/` hoặc log thô.
