#!/usr/bin/env python3

import argparse
import datetime
import glob
import json
import os


DEFAULT_SESSION_GLOB = os.path.expanduser("~/.openclaw/agents/main/sessions/*.jsonl")
DEFAULT_OUTPUT_PATH = os.path.join(os.getcwd(), "dist", "index.html")


def parse_timestamp(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if value > 1e12:
            return datetime.datetime.fromtimestamp(value / 1000, tz=datetime.timezone.utc)
        return datetime.datetime.fromtimestamp(value, tz=datetime.timezone.utc)
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return None
        if normalized.endswith("Z"):
            normalized = normalized[:-1] + "+00:00"
        try:
            parsed = datetime.datetime.fromisoformat(normalized)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=datetime.timezone.utc)
        return parsed.astimezone(datetime.timezone.utc)
    return None


def extract_text(content):
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return ""

    parts = []
    for item in content:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "text" and isinstance(item.get("text"), str):
            text = item["text"].strip()
            if text:
                parts.append(text)
    return "\n\n".join(parts).strip()


def truncate_text(text, limit):
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def scan_sessions(session_glob):
    records = []
    stats = {
        "files": 0,
        "lines": 0,
        "malformed_lines": 0,
        "messages_with_usage": 0,
    }

    for path in sorted(glob.glob(session_glob)):
        stats["files"] += 1
        session_id = os.path.splitext(os.path.basename(path))[0]
        previous_user_text = ""
        previous_user_at = None

        try:
            handle = open(path, "r", encoding="utf-8")
        except OSError:
            continue

        with handle:
            for line_number, raw_line in enumerate(handle, start=1):
                stats["lines"] += 1
                raw_line = raw_line.strip()
                if not raw_line:
                    continue

                try:
                    entry = json.loads(raw_line)
                except json.JSONDecodeError:
                    stats["malformed_lines"] += 1
                    continue

                if not isinstance(entry, dict):
                    continue

                message = entry.get("message")
                if not isinstance(message, dict):
                    continue

                role = message.get("role")
                message_text = extract_text(message.get("content"))
                message_ts = parse_timestamp(message.get("timestamp")) or parse_timestamp(entry.get("timestamp"))

                if role == "user":
                    previous_user_text = message_text
                    previous_user_at = message_ts
                    continue

                usage = message.get("usage")
                if role != "assistant" or not isinstance(usage, dict):
                    continue

                cost = usage.get("cost") or {}
                record = {
                    "sessionId": session_id,
                    "lineNumber": line_number,
                    "time": message_ts.isoformat().replace("+00:00", "Z") if message_ts else "",
                    "timestampMs": int(message_ts.timestamp() * 1000) if message_ts else 0,
                    "model": message.get("model") or entry.get("model") or "unknown",
                    "provider": message.get("provider") or entry.get("provider") or "",
                    "api": message.get("api") or entry.get("api") or "",
                    "input": int(usage.get("input") or 0),
                    "output": int(usage.get("output") or 0),
                    "cacheRead": int(usage.get("cacheRead") or 0),
                    "cacheWrite": int(usage.get("cacheWrite") or 0),
                    "totalTokens": int(usage.get("totalTokens") or 0),
                    "costInput": float(cost.get("input") or 0.0),
                    "costOutput": float(cost.get("output") or 0.0),
                    "costCacheRead": float(cost.get("cacheRead") or 0.0),
                    "costCacheWrite": float(cost.get("cacheWrite") or 0.0),
                    "costTotal": float(cost.get("total") or 0.0),
                    "context": int(usage.get("totalTokens") or 0),
                    "prompt": previous_user_text,
                    "promptShort": truncate_text(previous_user_text or "(no preceding user message)", 120),
                    "assistantText": truncate_text(message_text, 240),
                    "userTime": previous_user_at.isoformat().replace("+00:00", "Z") if previous_user_at else "",
                }
                records.append(record)
                stats["messages_with_usage"] += 1

    records.sort(key=lambda item: item["timestampMs"], reverse=True)
    return records, stats


def build_mock_records():
    now = datetime.datetime.now(datetime.timezone.utc).replace(minute=0, second=0, microsecond=0)
    rows = [
        ("gpt-5.4", 2, 18420, 3120, 26800, 1200, 0.2481, "Build a weekly view of cost by model and surface cache efficiency."),
        ("gpt-5.4-mini", 6, 8210, 1410, 9600, 420, 0.0619, "Refine the dashboard cards and tighten the filtering behavior."),
        ("gpt-5.3-codex", 12, 12480, 2860, 18320, 900, 0.1124, "Audit the generator script and cut accidental data leakage paths."),
        ("gpt-5.4", 18, 26300, 4720, 35600, 1800, 0.3417, "Prepare a static deployment flow that works from a phone."),
        ("gpt-5.2", 30, 10140, 2050, 11220, 530, 0.0742, "Generate a public mock dashboard for repository previews."),
        ("gpt-5.4-mini", 44, 6120, 980, 7800, 300, 0.0388, "Check recent usage records and explain spend spikes."),
        ("gpt-5.4", 60, 30110, 5280, 41800, 2100, 0.3895, "Add deployment documentation and make the output path configurable."),
        ("gpt-5.3-codex", 78, 9320, 1740, 12110, 640, 0.0814, "Create a safe deploy script that never commits generated HTML."),
        ("gpt-5.4-mini", 95, 5080, 840, 6900, 280, 0.0306, "Verify the mock build still renders the tables and summary cards."),
        ("gpt-5.2", 120, 7440, 1260, 8640, 410, 0.0497, "Summarize the dataset span and the total number of API calls."),
    ]

    records = []
    for index, (model, hours_ago, input_tokens, output_tokens, cache_read, cache_write, total_cost, prompt) in enumerate(rows, start=1):
        timestamp = now - datetime.timedelta(hours=hours_ago)
        provider = "openai" if model.startswith("gpt") else "unknown"
        total_tokens = input_tokens + output_tokens + cache_read + cache_write
        records.append({
            "sessionId": "mock-session-{}".format(index),
            "lineNumber": index,
            "time": timestamp.isoformat().replace("+00:00", "Z"),
            "timestampMs": int(timestamp.timestamp() * 1000),
            "model": model,
            "provider": provider,
            "api": "responses",
            "input": input_tokens,
            "output": output_tokens,
            "cacheRead": cache_read,
            "cacheWrite": cache_write,
            "totalTokens": total_tokens,
            "costInput": round(total_cost * 0.56, 4),
            "costOutput": round(total_cost * 0.31, 4),
            "costCacheRead": round(total_cost * 0.09, 4),
            "costCacheWrite": round(total_cost * 0.04, 4),
            "costTotal": total_cost,
            "context": total_tokens,
            "prompt": prompt,
            "promptShort": truncate_text(prompt, 120),
            "assistantText": "Mock assistant response for repository preview.",
            "userTime": timestamp.isoformat().replace("+00:00", "Z"),
        })

    records.sort(key=lambda item: item["timestampMs"], reverse=True)
    stats = {
        "files": 1,
        "lines": len(records),
        "malformed_lines": 0,
        "messages_with_usage": len(records),
    }
    return records, stats


def aggregate_models(records):
    by_model = {}
    for record in records:
        model = record["model"]
        if model not in by_model:
            by_model[model] = {
                "model": model,
                "calls": 0,
                "input": 0,
                "output": 0,
                "cacheRead": 0,
                "cacheWrite": 0,
                "totalTokens": 0,
                "totalCost": 0.0,
                "avgCost": 0.0,
            }
        bucket = by_model[model]
        bucket["calls"] += 1
        bucket["input"] += record["input"]
        bucket["output"] += record["output"]
        bucket["cacheRead"] += record["cacheRead"]
        bucket["cacheWrite"] += record["cacheWrite"]
        bucket["totalTokens"] += record["totalTokens"]
        bucket["totalCost"] += record["costTotal"]

    rows = []
    for row in by_model.values():
        row["avgCost"] = row["totalCost"] / row["calls"] if row["calls"] else 0.0
        rows.append(row)
    rows.sort(key=lambda item: (-item["totalCost"], item["model"]))
    return rows


def compute_summary(records):
    total_calls = len(records)
    total_cost = 0.0
    total_tokens = 0
    total_input = 0
    total_output = 0
    total_cache_read = 0
    total_cache_write = 0

    for record in records:
        total_cost += record["costTotal"]
        total_tokens += record["totalTokens"]
        total_input += record["input"]
        total_output += record["output"]
        total_cache_read += record["cacheRead"]
        total_cache_write += record["cacheWrite"]

    denominator = total_input + total_cache_read
    cache_hit_rate = (total_cache_read / denominator) if denominator else 0.0

    return {
        "totalCost": total_cost,
        "totalCalls": total_calls,
        "totalTokens": total_tokens,
        "totalInput": total_input,
        "totalOutput": total_output,
        "totalCacheRead": total_cache_read,
        "totalCacheWrite": total_cache_write,
        "cacheHitRate": cache_hit_rate,
    }


def json_for_html(value):
    return json.dumps(value, separators=(",", ":")).replace("</", "<\\/")


def build_html(data):
    data_json = json_for_html(data)
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Weber Cost Dashboard</title>
  <style>
    :root {
      --bg: #eef3f9;
      --surface: #ffffff;
      --surface-alt: #f4f8fc;
      --ink: #132033;
      --muted: #617086;
      --line: #d7e1ec;
      --header: #0d1726;
      --header-2: #19304c;
      --accent: #2874d9;
      --accent-strong: #145dc2;
      --accent-soft: rgba(40, 116, 217, 0.12);
      --good: #14804a;
      --shadow: 0 18px 40px rgba(13, 23, 38, 0.08);
      --radius: 18px;
      --touch-target: 44px;
    }

    * { box-sizing: border-box; }
    html { font-size: 16px; }
    html, body { margin: 0; padding: 0; background: var(--bg); color: var(--ink); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    body { min-height: 100vh; }
    button, input, select { font: inherit; }
    button { min-height: var(--touch-target); }

    .shell {
      min-height: 100vh;
      background:
        radial-gradient(circle at top right, rgba(40, 116, 217, 0.18), transparent 26%),
        linear-gradient(180deg, var(--header) 0, var(--header-2) 320px, var(--bg) 320px, var(--bg) 100%);
    }

    .container {
      width: min(1220px, calc(100vw - 24px));
      margin: 0 auto;
      padding: 18px 0 28px;
    }

    .hero {
      color: #fff;
      padding: 2px 0 22px;
    }

    .hero-top {
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 14px;
      align-items: flex-start;
      margin-bottom: 18px;
    }

    .eyebrow {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.12);
      color: rgba(255, 255, 255, 0.9);
      font-size: 0.875rem;
      letter-spacing: 0.02em;
    }

    h1 {
      margin: 12px 0 10px;
      font-size: clamp(2rem, 5vw, 3rem);
      line-height: 0.98;
      letter-spacing: -0.04em;
    }

    .subhead {
      margin: 0;
      max-width: 760px;
      color: rgba(255, 255, 255, 0.78);
      font-size: 1rem;
      line-height: 1.55;
    }

    .hero-actions {
      display: flex;
      width: 100%;
      gap: 10px;
      align-items: stretch;
      flex-wrap: wrap;
      justify-content: flex-start;
    }

    .button {
      border: 0;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-radius: 14px;
      padding: 12px 16px;
      cursor: pointer;
      transition: transform 0.15s ease, box-shadow 0.15s ease, background 0.15s ease;
      font-size: 1rem;
      line-height: 1.2;
    }

    .button:hover { transform: translateY(-1px); }
    .button.primary {
      background: #fff;
      color: var(--header);
      box-shadow: 0 10px 20px rgba(0, 0, 0, 0.16);
      font-weight: 600;
    }
    .button.secondary {
      background: rgba(255, 255, 255, 0.08);
      color: #fff;
      border: 1px solid rgba(255, 255, 255, 0.14);
    }
    .button.ghost {
      background: var(--surface-alt);
      color: var(--ink);
      border: 1px solid var(--line);
      font-weight: 600;
    }

    .toolbar {
      display: flex;
      flex-direction: column;
      gap: 12px;
      align-items: stretch;
      flex-wrap: wrap;
      margin-top: 18px;
    }

    .pill-group {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      padding: 8px;
      width: 100%;
      background: rgba(255, 255, 255, 0.12);
      border-radius: 20px;
      backdrop-filter: blur(16px);
    }

    .pill {
      border: 0;
      border-radius: 999px;
      min-height: var(--touch-target);
      padding: 10px 16px;
      background: transparent;
      color: rgba(255, 255, 255, 0.72);
      cursor: pointer;
      font-weight: 600;
      font-size: 1rem;
    }

    .pill.active {
      background: #fff;
      color: var(--accent-strong);
      box-shadow: 0 8px 18px rgba(0, 0, 0, 0.14);
    }

    .timestamp {
      color: rgba(255, 255, 255, 0.72);
      font-size: 1rem;
    }

    .grid {
      display: grid;
      gap: 18px;
    }

    .summary {
      grid-template-columns: 1fr;
      margin-top: -2px;
      margin-bottom: 18px;
    }

    .card, .panel {
      background: var(--surface);
      border: 1px solid rgba(219, 228, 240, 0.72);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
    }

    .card {
      padding: 18px;
    }

    .metric-label {
      color: var(--muted);
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      margin-bottom: 10px;
    }

    .metric-value {
      font-size: clamp(1.8rem, 7vw, 2.2rem);
      line-height: 1.1;
      letter-spacing: -0.04em;
      margin-bottom: 8px;
      font-weight: 700;
    }

    .metric-meta {
      color: var(--muted);
      font-size: 1rem;
    }

    .panel {
      overflow: hidden;
      margin-bottom: 18px;
    }

    .panel-head {
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 12px;
      align-items: flex-start;
      padding: 18px 18px 12px;
    }

    .panel-title {
      margin: 0;
      font-size: 1.1rem;
      letter-spacing: -0.02em;
    }

    .panel-subtitle {
      margin: 5px 0 0;
      color: var(--muted);
      font-size: 1rem;
      line-height: 1.45;
    }

    .panel-actions {
      display: flex;
      width: 100%;
      justify-content: flex-start;
    }

    .table-tools {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 0 18px 10px;
    }

    .scroll-indicator {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      color: var(--muted);
      font-size: 0.85rem;
      white-space: nowrap;
    }

    .mobile-only {
      display: inline-flex;
    }

    .table-wrap {
      position: relative;
      overflow: auto;
      border-top: 1px solid var(--line);
      -webkit-overflow-scrolling: touch;
      scroll-behavior: smooth;
      overscroll-behavior-x: contain;
      scrollbar-gutter: stable both-edges;
    }

    .table-wrap::after {
      content: "";
      position: sticky;
      right: 0;
      top: 0;
      float: right;
      width: 28px;
      height: 100%;
      pointer-events: none;
      background: linear-gradient(270deg, rgba(244, 248, 252, 0.98) 0%, rgba(244, 248, 252, 0) 100%);
    }

    .table-wrap.scrolled-end::after {
      opacity: 0;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      min-width: 720px;
    }

    th, td {
      padding: 13px 14px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
      font-size: 1rem;
    }

    th {
      position: sticky;
      top: 0;
      background: var(--surface-alt);
      color: var(--muted);
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      z-index: 1;
      cursor: default;
      white-space: nowrap;
    }

    th.sortable {
      cursor: pointer;
      user-select: none;
    }

    th.sortable:hover {
      color: var(--accent-strong);
    }

    tbody tr:hover {
      background: #f8fbff;
    }

    .mono {
      font-variant-numeric: tabular-nums;
      white-space: nowrap;
    }

    .model-tag {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      min-height: 34px;
      padding: 7px 12px;
      border-radius: 999px;
      background: var(--accent-soft);
      color: var(--accent-strong);
      font-weight: 600;
    }

    .prompt-button {
      border: 0;
      background: transparent;
      min-height: var(--touch-target);
      padding: 0;
      color: var(--accent-strong);
      cursor: pointer;
      text-align: left;
      line-height: 1.45;
      font-size: 1rem;
    }

    .prompt-button:hover {
      text-decoration: underline;
    }

    .muted {
      color: var(--muted);
    }

    .empty {
      padding: 22px 18px 26px;
      color: var(--muted);
      font-size: 1rem;
    }

    .modal-backdrop {
      position: fixed;
      inset: 0;
      background: rgba(6, 14, 24, 0.6);
      display: none;
      align-items: center;
      justify-content: center;
      padding: 20px;
      z-index: 30;
    }

    .modal-backdrop.open {
      display: flex;
    }

    .modal {
      width: min(760px, 100%);
      max-height: min(80vh, 900px);
      overflow: auto;
      background: #fff;
      border-radius: 20px;
      box-shadow: 0 26px 60px rgba(0, 0, 0, 0.24);
    }

    .modal-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      padding: 18px 18px 12px;
      border-bottom: 1px solid var(--line);
    }

    .modal-body {
      padding: 18px 18px 22px;
    }

    .modal pre {
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      line-height: 1.6;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 0.9rem;
      color: #1d2c40;
    }

    .close {
      border: 0;
      background: #eef4fb;
      color: var(--ink);
      width: var(--touch-target);
      height: var(--touch-target);
      border-radius: 999px;
      cursor: pointer;
      font-size: 18px;
    }

    .footnote {
      margin-top: 10px;
      color: var(--muted);
      font-size: 1rem;
      line-height: 1.55;
    }

    .recent-table .mobile-optional {
      display: none;
    }

    .panel.expanded .recent-table .mobile-optional {
      display: table-cell;
    }

    .recent-table {
      min-width: 620px;
    }

    .model-table {
      min-width: 760px;
    }

    @media (min-width: 768px) {
      .container {
        width: min(1220px, calc(100vw - 32px));
        padding: 28px 0 40px;
      }

      .hero {
        padding: 6px 0 28px;
      }

      .hero-top {
        flex-direction: row;
        gap: 16px;
        margin-bottom: 24px;
      }

      .hero-actions {
        width: auto;
        align-items: center;
        justify-content: flex-end;
      }

      .toolbar {
        flex-direction: row;
        align-items: center;
        margin-top: 22px;
      }

      .pill-group {
        display: inline-flex;
        width: auto;
        border-radius: 999px;
      }

      .summary {
        grid-template-columns: repeat(2, minmax(0, 1fr));
        margin-bottom: 24px;
      }

      .card {
        padding: 20px;
      }

      .panel-head {
        flex-direction: row;
        align-items: center;
        padding: 20px 22px 14px;
      }

      .panel-actions {
        width: auto;
        justify-content: flex-end;
      }

      .table-tools {
        padding: 0 22px 10px;
      }

      .empty {
        padding: 24px 22px 30px;
      }

      .modal-head {
        padding: 20px 22px 12px;
      }

      .modal-body {
        padding: 20px 22px 24px;
      }

      th, td {
        padding: 14px 16px;
      }

      .recent-table .mobile-optional {
        display: table-cell;
      }

      .mobile-only {
        display: none;
      }

      .recent-table,
      .model-table {
        min-width: 100%;
      }
    }

    @media (min-width: 1024px) {
      .summary {
        grid-template-columns: repeat(4, minmax(0, 1fr));
      }
    }

    @media (max-width: 767px) {
      .button.primary {
        width: 100%;
      }

      .timestamp {
        width: 100%;
      }

      .table-tools {
        flex-wrap: wrap;
      }

      .scroll-indicator {
        width: 100%;
      }
    }
  </style>
</head>
<body>
  <div class="shell">
    <div class="container">
      <section class="hero">
        <div class="hero-top">
          <div>
            <div class="eyebrow">OpenClaw Agent Usage</div>
            <h1>Weber Cost Dashboard</h1>
            <p class="subhead">Standalone cost monitoring for assistant API usage across all main-session JSONL logs. Filter the embedded dataset client-side without any backend.</p>
          </div>
          <div class="hero-actions">
            <button class="button primary" id="refresh-button" type="button">Refresh Data</button>
            <div class="timestamp" id="generated-at"></div>
          </div>
        </div>
        <div class="toolbar">
          <div class="pill-group" id="time-range-pills">
            <button class="pill" data-range="1h" type="button">1h</button>
            <button class="pill" data-range="6h" type="button">6h</button>
            <button class="pill active" data-range="24h" type="button">24h</button>
            <button class="pill" data-range="7d" type="button">7d</button>
            <button class="pill" data-range="30d" type="button">30d</button>
            <button class="pill" data-range="all" type="button">All</button>
          </div>
          <div class="timestamp" id="range-caption"></div>
        </div>
      </section>

      <section class="grid summary">
        <article class="card">
          <div class="metric-label">Total Cost</div>
          <div class="metric-value" id="metric-cost">$0.0000</div>
          <div class="metric-meta" id="metric-cost-meta"></div>
        </article>
        <article class="card">
          <div class="metric-label">Total Calls</div>
          <div class="metric-value" id="metric-calls">0</div>
          <div class="metric-meta" id="metric-calls-meta"></div>
        </article>
        <article class="card">
          <div class="metric-label">Total Tokens</div>
          <div class="metric-value" id="metric-tokens">0</div>
          <div class="metric-meta" id="metric-tokens-meta"></div>
        </article>
        <article class="card">
          <div class="metric-label">Cache Hit Rate</div>
          <div class="metric-value" id="metric-cache">0.0%</div>
          <div class="metric-meta" id="metric-cache-meta"></div>
        </article>
      </section>

      <section class="panel" id="recent-panel">
        <div class="panel-head">
          <div>
            <h2 class="panel-title">Cost by Model</h2>
            <p class="panel-subtitle">Aggregated assistant usage grouped by model for the selected time range.</p>
          </div>
        </div>
        <div class="table-tools">
          <div class="scroll-indicator">Swipe to view more columns</div>
        </div>
        <div class="table-wrap">
          <table class="model-table">
            <thead>
              <tr>
                <th>Model</th>
                <th>Calls</th>
                <th>Input Tokens</th>
                <th>Output Tokens</th>
                <th>Cache Read</th>
                <th>Cache Write</th>
                <th>Total Cost</th>
                <th>Avg Cost / Call</th>
              </tr>
            </thead>
            <tbody id="model-table-body"></tbody>
          </table>
        </div>
        <div class="empty" id="model-empty" hidden>No usage records match the current filter.</div>
      </section>

      <section class="panel">
        <div class="panel-head">
          <div>
            <h2 class="panel-title">Recent API Calls</h2>
            <p class="panel-subtitle">Newest assistant calls first. Click any prompt to view the full preceding user message.</p>
          </div>
          <div class="panel-actions">
            <button class="button ghost mobile-only" id="recent-toggle" type="button" aria-expanded="false">View Full</button>
          </div>
        </div>
        <div class="table-tools">
          <div class="scroll-indicator">Swipe to view more columns</div>
        </div>
        <div class="table-wrap">
          <table class="recent-table">
            <thead>
              <tr>
                <th class="sortable" data-sort-key="timestampMs">Time</th>
                <th class="sortable" data-sort-key="model">Model</th>
                <th class="sortable" data-sort-key="input">Input</th>
                <th class="sortable" data-sort-key="output">Output</th>
                <th class="sortable mobile-optional" data-sort-key="cacheRead">Cache Read</th>
                <th class="sortable mobile-optional" data-sort-key="cacheWrite">Cache Write</th>
                <th class="sortable mobile-optional" data-sort-key="context">Context</th>
                <th class="sortable" data-sort-key="costTotal">Cost</th>
                <th>Prompt</th>
              </tr>
            </thead>
            <tbody id="recent-table-body"></tbody>
          </table>
        </div>
        <div class="empty" id="recent-empty" hidden>No recent calls match the current filter.</div>
      </section>

      <div class="footnote" id="footnote"></div>
    </div>
  </div>

  <div class="modal-backdrop" id="modal-backdrop" aria-hidden="true">
    <div class="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title">
      <div class="modal-head">
        <div>
          <strong id="modal-title">Prompt</strong>
          <div class="muted" id="modal-meta"></div>
        </div>
        <button class="close" id="modal-close" type="button" aria-label="Close">×</button>
      </div>
      <div class="modal-body">
        <pre id="modal-content"></pre>
      </div>
    </div>
  </div>

  <script id="dashboard-data" type="application/json">__DATA__</script>
  <script>
    const dashboardData = JSON.parse(document.getElementById("dashboard-data").textContent);
    const ranges = {
      "1h": 60 * 60 * 1000,
      "6h": 6 * 60 * 60 * 1000,
      "24h": 24 * 60 * 60 * 1000,
      "7d": 7 * 24 * 60 * 60 * 1000,
      "30d": 30 * 24 * 60 * 60 * 1000,
      "all": null
    };

    let state = {
      range: "24h",
      sortKey: "timestampMs",
      sortDirection: "desc",
      recentExpanded: false
    };

    const fmtInt = new Intl.NumberFormat("en-US");
    const fmtPct = new Intl.NumberFormat("en-US", { style: "percent", minimumFractionDigits: 1, maximumFractionDigits: 1 });
    const fmtCost = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 4, maximumFractionDigits: 4 });
    const fmtDate = new Intl.DateTimeFormat("en-US", {
      year: "numeric",
      month: "short",
      day: "2-digit",
      hour: "numeric",
      minute: "2-digit"
    });

    function escapeHtml(value) {
      return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
    }

    function getFilteredRecords() {
      const duration = ranges[state.range];
      if (duration === null) {
        return dashboardData.records.slice();
      }
      const cutoff = dashboardData.meta.latestTimestampMs - duration;
      return dashboardData.records.filter((record) => record.timestampMs >= cutoff);
    }

    function summarize(records) {
      const summary = {
        totalCost: 0,
        totalCalls: records.length,
        totalTokens: 0,
        totalInput: 0,
        totalOutput: 0,
        totalCacheRead: 0,
        totalCacheWrite: 0,
        cacheHitRate: 0
      };
      for (const record of records) {
        summary.totalCost += record.costTotal;
        summary.totalTokens += record.totalTokens;
        summary.totalInput += record.input;
        summary.totalOutput += record.output;
        summary.totalCacheRead += record.cacheRead;
        summary.totalCacheWrite += record.cacheWrite;
      }
      const denominator = summary.totalInput + summary.totalCacheRead;
      summary.cacheHitRate = denominator ? summary.totalCacheRead / denominator : 0;
      return summary;
    }

    function aggregateModels(records) {
      const models = new Map();
      for (const record of records) {
        if (!models.has(record.model)) {
          models.set(record.model, {
            model: record.model,
            calls: 0,
            input: 0,
            output: 0,
            cacheRead: 0,
            cacheWrite: 0,
            totalCost: 0
          });
        }
        const bucket = models.get(record.model);
        bucket.calls += 1;
        bucket.input += record.input;
        bucket.output += record.output;
        bucket.cacheRead += record.cacheRead;
        bucket.cacheWrite += record.cacheWrite;
        bucket.totalCost += record.costTotal;
      }
      return Array.from(models.values())
        .map((row) => ({ ...row, avgCost: row.calls ? row.totalCost / row.calls : 0 }))
        .sort((a, b) => b.totalCost - a.totalCost || a.model.localeCompare(b.model));
    }

    function sortRecords(records) {
      const sorted = records.slice();
      const direction = state.sortDirection === "asc" ? 1 : -1;
      sorted.sort((a, b) => {
        const av = a[state.sortKey];
        const bv = b[state.sortKey];
        if (typeof av === "string" && typeof bv === "string") {
          return av.localeCompare(bv) * direction;
        }
        return ((av > bv) - (av < bv)) * direction;
      });
      return sorted;
    }

    function renderSummary(summary) {
      document.getElementById("metric-cost").textContent = fmtCost.format(summary.totalCost);
      document.getElementById("metric-cost-meta").textContent = summary.totalCalls ? fmtCost.format(summary.totalCost / summary.totalCalls) + " average per call" : "No calls in range";
      document.getElementById("metric-calls").textContent = fmtInt.format(summary.totalCalls);
      document.getElementById("metric-calls-meta").textContent = fmtInt.format(summary.totalInput + summary.totalOutput) + " direct prompt/response tokens";
      document.getElementById("metric-tokens").textContent = fmtInt.format(summary.totalTokens);
      document.getElementById("metric-tokens-meta").textContent = fmtInt.format(summary.totalCacheRead) + " cache read, " + fmtInt.format(summary.totalCacheWrite) + " cache write";
      document.getElementById("metric-cache").textContent = fmtPct.format(summary.cacheHitRate);
      document.getElementById("metric-cache-meta").textContent = fmtInt.format(summary.totalCacheRead) + " cached tokens reused";
    }

    function renderModelTable(rows) {
      const tbody = document.getElementById("model-table-body");
      const empty = document.getElementById("model-empty");
      if (!rows.length) {
        tbody.innerHTML = "";
        empty.hidden = false;
        return;
      }
      empty.hidden = true;
      tbody.innerHTML = rows.map((row) => `
        <tr>
          <td><span class="model-tag">${escapeHtml(row.model)}</span></td>
          <td class="mono">${fmtInt.format(row.calls)}</td>
          <td class="mono">${fmtInt.format(row.input)}</td>
          <td class="mono">${fmtInt.format(row.output)}</td>
          <td class="mono">${fmtInt.format(row.cacheRead)}</td>
          <td class="mono">${fmtInt.format(row.cacheWrite)}</td>
          <td class="mono">${fmtCost.format(row.totalCost)}</td>
          <td class="mono">${fmtCost.format(row.avgCost)}</td>
        </tr>
      `).join("");
    }

    function renderRecentTable(records) {
      const tbody = document.getElementById("recent-table-body");
      const empty = document.getElementById("recent-empty");
      if (!records.length) {
        tbody.innerHTML = "";
        empty.hidden = false;
        return;
      }
      empty.hidden = true;
      tbody.innerHTML = records.map((record, index) => `
        <tr>
          <td class="mono">${fmtDate.format(new Date(record.timestampMs))}</td>
          <td>${escapeHtml(record.model)}</td>
          <td class="mono">${fmtInt.format(record.input)}</td>
          <td class="mono">${fmtInt.format(record.output)}</td>
          <td class="mono mobile-optional">${fmtInt.format(record.cacheRead)}</td>
          <td class="mono mobile-optional">${fmtInt.format(record.cacheWrite)}</td>
          <td class="mono mobile-optional">${fmtInt.format(record.context)}</td>
          <td class="mono">${fmtCost.format(record.costTotal)}</td>
          <td><button class="prompt-button" type="button" data-index="${index}">${escapeHtml(record.promptShort || "(no prompt)")}</button></td>
        </tr>
      `).join("");

      Array.from(tbody.querySelectorAll(".prompt-button")).forEach((button) => {
        button.addEventListener("click", () => {
          const record = records[Number(button.dataset.index)];
          openModal(record);
        });
      });
    }

    function syncTableWrapIndicators() {
      Array.from(document.querySelectorAll(".table-wrap")).forEach((wrap) => {
        const maxScroll = wrap.scrollWidth - wrap.clientWidth;
        const atEnd = maxScroll <= 2 || wrap.scrollLeft >= maxScroll - 2;
        wrap.classList.toggle("scrolled-end", atEnd);
      });
    }

    function renderRecentToggle() {
      const panel = document.getElementById("recent-panel");
      const button = document.getElementById("recent-toggle");
      if (!panel || !button) {
        return;
      }
      panel.classList.toggle("expanded", state.recentExpanded);
      button.textContent = state.recentExpanded ? "Show Less" : "View Full";
      button.setAttribute("aria-expanded", state.recentExpanded ? "true" : "false");
    }

    function renderMeta(records) {
      const first = records[records.length - 1];
      const latest = records[0];
      const label = state.range === "all" ? "Showing all embedded records" : "Showing records from the last " + state.range;
      const span = latest ? fmtDate.format(new Date(latest.timestampMs)) : "n/a";
      const start = first ? fmtDate.format(new Date(first.timestampMs)) : "n/a";
      document.getElementById("range-caption").textContent = label + " • " + fmtInt.format(records.length) + " calls";
      document.getElementById("generated-at").textContent = "Generated " + fmtDate.format(new Date(dashboardData.meta.generatedAtMs));
      document.getElementById("footnote").textContent =
        "Source: " + (dashboardData.meta.sourceLabel || "unknown") +
        " • " +
        "Dataset span: " + start + " to " + span +
        " • Files scanned: " + fmtInt.format(dashboardData.meta.filesScanned) +
        " • Malformed lines skipped: " + fmtInt.format(dashboardData.meta.malformedLines);
    }

    function render() {
      const filtered = getFilteredRecords();
      const summary = summarize(filtered);
      renderSummary(summary);
      renderModelTable(aggregateModels(filtered));
      renderRecentTable(sortRecords(filtered));
      renderMeta(filtered);
      renderRecentToggle();
      syncTableWrapIndicators();

      Array.from(document.querySelectorAll(".pill")).forEach((pill) => {
        pill.classList.toggle("active", pill.dataset.range === state.range);
      });
    }

    function openModal(record) {
      document.getElementById("modal-title").textContent = "Prompt";
      document.getElementById("modal-meta").textContent =
        (record.model || "unknown model") + " • " + fmtDate.format(new Date(record.timestampMs)) + " • " + fmtCost.format(record.costTotal);
      document.getElementById("modal-content").textContent = record.prompt || "(no preceding user message found)";
      document.getElementById("modal-backdrop").classList.add("open");
      document.getElementById("modal-backdrop").setAttribute("aria-hidden", "false");
    }

    function closeModal() {
      document.getElementById("modal-backdrop").classList.remove("open");
      document.getElementById("modal-backdrop").setAttribute("aria-hidden", "true");
    }

    document.getElementById("time-range-pills").addEventListener("click", (event) => {
      const pill = event.target.closest(".pill");
      if (!pill) return;
      state.range = pill.dataset.range;
      render();
    });

    Array.from(document.querySelectorAll("th.sortable")).forEach((th) => {
      th.addEventListener("click", () => {
        const key = th.dataset.sortKey;
        if (state.sortKey === key) {
          state.sortDirection = state.sortDirection === "desc" ? "asc" : "desc";
        } else {
          state.sortKey = key;
          state.sortDirection = key === "model" ? "asc" : "desc";
        }
        render();
      });
    });

    document.getElementById("refresh-button").addEventListener("click", () => {
      window.alert("Re-run: python3 generate-dashboard.py --output dist/index.html\\n\\nThis dashboard is static and refreshes by regenerating dist/index.html from ~/.openclaw/agents/main/sessions/*.jsonl");
    });

    document.getElementById("recent-toggle").addEventListener("click", () => {
      state.recentExpanded = !state.recentExpanded;
      renderRecentToggle();
      syncTableWrapIndicators();
    });

    document.getElementById("modal-close").addEventListener("click", closeModal);
    document.getElementById("modal-backdrop").addEventListener("click", (event) => {
      if (event.target.id === "modal-backdrop") {
        closeModal();
      }
    });
    window.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        closeModal();
      }
    });
    Array.from(document.querySelectorAll(".table-wrap")).forEach((wrap) => {
      wrap.addEventListener("scroll", syncTableWrapIndicators, { passive: true });
    });
    window.addEventListener("resize", syncTableWrapIndicators);

    render();
  </script>
</body>
</html>
""".replace("__DATA__", data_json)


def build_payload(records, scan_stats, source_label):
    models = aggregate_models(records)
    summary = compute_summary(records)

    latest_timestamp = records[0]["timestampMs"] if records else int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000)
    generated_at = datetime.datetime.now(datetime.timezone.utc)
    return {
        "meta": {
            "generatedAt": generated_at.isoformat().replace("+00:00", "Z"),
            "generatedAtMs": int(generated_at.timestamp() * 1000),
            "latestTimestampMs": latest_timestamp,
            "filesScanned": scan_stats["files"],
            "linesScanned": scan_stats["lines"],
            "malformedLines": scan_stats["malformed_lines"],
            "messagesWithUsage": scan_stats["messages_with_usage"],
            "sourceLabel": source_label,
        },
        "summary": summary,
        "models": models,
        "records": records,
    }


def write_html(output_path, html):
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write(html)


def parse_args():
    parser = argparse.ArgumentParser(description="Generate a standalone OpenClaw cost dashboard.")
    parser.add_argument("--session-glob", default=DEFAULT_SESSION_GLOB, help="Glob for OpenClaw session JSONL files.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH, help="Output HTML path.")
    parser.add_argument("--mock", action="store_true", help="Generate a synthetic dashboard with mock usage data.")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.mock:
        records, scan_stats = build_mock_records()
        source_label = "Mock data for public preview"
    else:
        records, scan_stats = scan_sessions(args.session_glob)
        source_label = "Local OpenClaw session logs"

    payload = build_payload(records, scan_stats, source_label)
    html = build_html(payload)
    write_html(args.output, html)

    print("Weber Cost Dashboard")
    print("Output:", args.output)
    print("Data source:", source_label)
    print("Files scanned:", scan_stats["files"])
    print("Lines scanned:", scan_stats["lines"])
    print("Malformed lines skipped:", scan_stats["malformed_lines"])
    print("Usage records:", len(records))
    print("Models:", len(payload["models"]))
    print("Total cost: ${:.4f}".format(payload["summary"]["totalCost"]))
    print("Total calls:", payload["summary"]["totalCalls"])
    print("Total tokens:", payload["summary"]["totalTokens"])
    print("Cache hit rate: {:.1%}".format(payload["summary"]["cacheHitRate"]))


if __name__ == "__main__":
    main()
