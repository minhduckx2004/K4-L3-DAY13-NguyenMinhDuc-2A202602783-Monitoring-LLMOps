"""Local six-panel dashboard backed by the last 60 minutes of JSONL logs."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from statistics import mean

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = yaml.safe_load((ROOT / 'config/dashboard.yaml').read_text(encoding='utf-8'))['dashboard']
LOG = ROOT / CONFIG['panels'][0]['source']


def percentile(values, p):
    if not values:
        return 0
    values = sorted(values)
    return values[max(0, min(len(values) - 1, round(p / 100 * len(values) + .5) - 1))]


def snapshot():
    now = datetime.now(timezone.utc)
    records = []
    if LOG.exists():
        for line in LOG.read_text(encoding='utf-8').splitlines():
            try:
                row = json.loads(line)
                ts = datetime.fromisoformat(row['ts'].replace('Z', '+00:00'))
                if now - timedelta(minutes=60) <= ts <= now + timedelta(seconds=5):
                    row['_minute'] = ts.strftime('%H:%M')
                    records.append(row)
            except (ValueError, KeyError, TypeError):
                continue
    received = [r for r in records if r.get('event') == 'request_received']
    sent = [r for r in records if r.get('event') == 'response_sent']
    failed = [r for r in records if r.get('event') == 'request_failed']
    by_minute = defaultdict(lambda: {'traffic': 0, 'errors': 0, 'cost': 0, 'latencies': []})
    for r in received:
        by_minute[r['_minute']]['traffic'] += 1
    for r in failed:
        by_minute[r['_minute']]['errors'] += 1
    for r in sent:
        by_minute[r['_minute']]['cost'] += r.get('cost_usd', 0)
        by_minute[r['_minute']]['latencies'].append(r.get('latency_ms', 0))
    latencies = [r.get('latency_ms', 0) for r in sent]
    attempts = [r for r in records if r.get('tool_success') is not None]
    errors = Counter(r.get('error_type', 'unknown') for r in failed)
    total = len(received)
    good = sum(r.get('latency_ms', float('inf')) <= 3000 for r in sent)
    remaining = max(0, total * .005 - (total - good))
    return {
        'panels': CONFIG['panels'], 'time_range_minutes': 60, 'refresh_seconds': CONFIG['refresh_seconds'],
        'updated_at': now.isoformat(), 'minutes': sorted(by_minute),
        'series': {key: [by_minute[m][key] if key != 'latencies' else percentile(by_minute[m][key], 95)
                         for m in sorted(by_minute)] for key in ('traffic', 'errors', 'cost', 'latencies')},
        'values': {
            'latency': {'P50': percentile(latencies, 50), 'P95': percentile(latencies, 95),
                        'P99': percentile(latencies, 99), 'TTFT P95': percentile([r.get('ttft_ms', 0) for r in sent], 95)},
            'traffic': {'requests': total, 'requests/min': round(total / 60, 2)},
            'errors': {'error rate %': round(100 * len(failed) / total, 2) if total else 0,
                       'breakdown': dict(errors), 'retrieval success %': round(100 * sum(r['tool_success'] is True for r in attempts) / len(attempts), 2) if attempts else 0},
            'cost': {'total USD': round(sum(r.get('cost_usd', 0) for r in sent), 6)},
            'tokens': {'input': sum(r.get('tokens_in', 0) for r in sent), 'output': sum(r.get('tokens_out', 0) for r in sent)},
            'quality': {'mean': round(mean([r.get('quality_score', 0) for r in sent]), 3) if sent else 0},
        },
        'slo': {'good': good, 'total': total, 'error_budget_requests_remaining': round(remaining, 3),
                'sli_pct': round(good / total * 100, 2) if total else None},
    }


PAGE = '''<!doctype html><html lang="vi"><meta charset="utf-8"><title>Day 13 • Observability</title>
<style>body{font:16px system-ui;background:#0e1527;color:#e9edf7;margin:24px;max-width:1400px}header{display:flex;justify-content:space-between;align-items:center}small{color:#aebbd5}#grid{display:grid;grid-template-columns:repeat(3,minmax(260px,1fr));gap:18px}.card{background:#18243b;border:1px solid #344461;border-radius:14px;padding:20px;min-height:220px}h2{font-size:18px;margin:0 0 14px}.value{font-size:28px;font-weight:700;color:#68d5c5}.details{line-height:1.8}.limit{font-size:13px;color:#eec581}svg{width:100%;height:70px;margin-top:12px}footer{margin:24px 0;color:#aebbd5}@media(max-width:900px){#grid{grid-template-columns:1fr}}</style>
<header><div><h1>Monitoring & LLMOps</h1><small>Window: last 60 minutes · refresh: 30 seconds · source: data/logs.jsonl</small></div><small id="updated"></small></header><p id="slo"></p><main id="grid"></main><footer>Thresholds and SLO lines follow config/dashboard.yaml · No raw request data is shown.</footer>
<script>
function chart(arr, threshold){if(!arr.length)return '<small>No samples yet</small>';let top=Math.max(1,threshold,...arr)*1.15;let pts=arr.map((v,i)=>`${i*100/Math.max(1,arr.length-1)},${65-v/top*60}`).join(' ');let y=65-threshold/top*60;return `<svg viewBox="0 0 100 70" preserveAspectRatio="none"><line x1="0" x2="100" y1="${y}" y2="${y}" stroke="#eec581" stroke-dasharray="2 2"/><polyline points="${pts}" fill="none" stroke="#68d5c5" stroke-width="2" vector-effect="non-scaling-stroke"/></svg>`}
async function refresh(){let d=await(await fetch('/data')).json();document.getElementById('updated').textContent='Updated '+new Date(d.updated_at).toLocaleTimeString();document.getElementById('slo').textContent=`SLO 99.5% fast successful requests (≤3000 ms) · ${d.slo.good}/${d.slo.total} good · SLI ${d.slo.sli_pct??'—'}% · remaining error budget ${d.slo.error_budget_requests_remaining} requests`;let keys={latency:'latencies',traffic:'traffic',errors:'errors',cost:'cost'};document.getElementById('grid').innerHTML=d.panels.map(p=>{let v=d.values[p.id],t=p.threshold;let entries=Object.entries(v).map(([k,x])=>`<div>${k}: <b>${typeof x==='object'?JSON.stringify(x):x}</b></div>`).join('');return `<section class="card"><h2>${p.title}</h2><div class="value">${Object.values(v)[0]}</div><div class="details">${entries}</div><div class="limit">SLO line: ${t.aggregation} ${t.operator==='lte'?'≤':'≥'} ${t.value} ${p.unit}</div>${keys[p.id]?chart(d.series[keys[p.id]],t.value):''}</section>`}).join('')}
refresh();setInterval(refresh,30000);
</script></html>'''


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ('/', '/data'):
            self.send_error(404)
            return
        payload = json.dumps(snapshot(), ensure_ascii=False).encode() if self.path == '/data' else PAGE.encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8' if self.path == '/data' else 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


if __name__ == '__main__':
    print('Dashboard: http://127.0.0.1:8501')
    ThreadingHTTPServer(('127.0.0.1', 8501), Handler).serve_forever()
