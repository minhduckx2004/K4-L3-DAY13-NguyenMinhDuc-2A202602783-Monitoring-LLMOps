# Chạy và nộp trên Windows PowerShell

1. Giải nén, mở folder gốc trong PyCharm/PowerShell. `python --version` phải từ 3.11. Tạo môi trường:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Nếu PowerShell chặn activate: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` rồi activate lại. Trong Langfuse Cloud, tạo project `day13-k4-l3a-2A202602783`, prompt và API key của **chính mình**; điền vào `.env` (không gửi key vào chat, không commit). Xem [prompt guide](PROMPT_VERSIONING.md).

2. Terminal 1: `uvicorn app.main:app --reload --env-file .env`. Mở `http://127.0.0.1:8000/health`; `ok` phải true và `tracing_enabled` phải true.

3. Terminal 2, từ thư mục gốc:

```powershell
python scripts/load_test.py --concurrency 5
python scripts/validate_logs.py
python scripts/validate_dashboard.py
python -m pytest -q
python scripts/dashboard.py
```

Mở `http://127.0.0.1:8501`; chụp sáu panel. Nếu log có baseline cũ, lưu evidence cũ rồi xóa `data/logs.jsonl`, restart API và chạy lại load test trước validator. Nếu `tracing_enabled=false` hoặc prompt_source khác `langfuse`, kiểm tra `.env`, project, URL và restart. Kiểm tra ít nhất 10 traces đúng project; chụp list, waterfall, metadata. Tạo prompt versions, chạy baseline/candidate và promote/rollback theo guide, điền trace IDs trong report.

4. Practice trước challenge:

```powershell
python scripts/inject_incident.py --scenario rag_slow
python scripts/load_test.py --concurrency 5
python scripts/inject_incident.py --scenario rag_slow --disable
```

5. **Chỉ khi Lab Coach release:** đặt file gốc `config/challenge.json`; kiểm tra `challenge_id=day13-k4-l3a-monitoring-llmops-v1`, không sửa file. Chạy:

```powershell
python scripts/inject_incident.py
python scripts/load_test.py --challenge --concurrency 5
```

Ghi time window, metric bất thường; từ JSONL lấy log `correlation_id`, trong Langfuse tìm trace cùng ID và so span. Chụp evidence, điền root cause/fix/prevention vào `submission/REPORT.md`. Nếu cần tắt incident, dùng `python scripts/inject_incident.py --scenario <tên-scenario> --disable` sau khi xác định tên từ file Lab Coach; không đưa file đó vào repo.

6. Chụp các ảnh còn thiếu theo [evidence checklist](SUBMISSION.md) vào `submission/evidence`, cập nhật liên kết và số liệu thật trong `submission/REPORT.md`. Chạy lại tests/validators trên source cuối. Kiểm tra `git status --short` và `git diff --cached --name-only`, bảo đảm không có `.env`, `config/challenge.json`, `data/logs.jsonl`, `.venv` hay key. Sau đó:

```powershell
git add app config/dashboard.yaml config/slo.yaml config/alert_rules.yaml docs scripts tests submission README.md requirements.txt .gitignore
git status --short
git commit -m "Complete Day 13 observability lab"
git push origin main
git rev-parse HEAD
```

Cập nhật report với SHA cuối sẽ cần thêm một commit mới; **SHA nộp là SHA của commit mới nhất sau khi cập nhật report**, rồi push. Nộp trên LMS/Codelabs **URL repo cá nhân + commit SHA cuối**. Không nộp ZIP thay repo nếu rubric không yêu cầu.
