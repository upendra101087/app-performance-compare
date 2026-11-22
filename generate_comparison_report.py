#!/usr/bin/env python3
"""
Performance Benchmark Report Generator
Renders an interactive HTML Dashboard with charts comparing Target App vs Competitor Apps.
Highlights clear category winners and crowns the Overall Performance Champion:
- Cold & Hot Startup Time (Fastest launch wins)
- CPU % (Lowest utilization wins)
- Memory PSS (Smallest RAM footprint wins)
- Jank Rate & FPS (Smoothest UI & closest to 60 FPS wins)
- Network Data (Most network-efficient wins)
- Disk I/O (Least disk churn wins)
"""

import json
import os
import sys
from typing import Dict, Any, Tuple, List

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_REPORT_PATH = os.path.join(SCRIPT_DIR, "performance_benchmark_report.html")

SAMPLE_BENCHMARK_DATA = {
    "Angelone": {
        "package": "com.msf.angelmobile",
        "startup": {
            "cold_start_runs_ms": [483, 496],
            "cold_start_median_ms": 496,
            "hot_start_runs_ms": [58, 42, 80],
            "hot_start_median_ms": 42
        },
        "performance": {
            "cpu": {"avg_percent": 7.96, "max_percent": 14.5, "p95_percent": 11.2},
            "memory": {"avg_pss_mb": 257.34, "max_pss_mb": 316.59},
            "rendering": {"approx_fps": 53.3, "jank_percentage": 22.35, "p50_frame_time_ms": 18.2, "p95_frame_time_ms": 28.5},
            "disk": {"read_kb": 1450.0, "write_kb": 680.0},
            "network": {"download_kb": 429.15, "upload_kb": 34.2}
        }
    },
    "Groww": {
        "package": "com.nextbillion.groww",
        "startup": {
            "cold_start_runs_ms": [529, 525, 543],
            "cold_start_median_ms": 525,
            "hot_start_runs_ms": [72, 49, 59],
            "hot_start_median_ms": 49
        },
        "performance": {
            "cpu": {"avg_percent": 32.09, "max_percent": 48.2, "p95_percent": 42.0},
            "memory": {"avg_pss_mb": 356.37, "max_pss_mb": 409.36},
            "rendering": {"approx_fps": 57.9, "jank_percentage": 7.03, "p50_frame_time_ms": 16.4, "p95_frame_time_ms": 19.8},
            "disk": {"read_kb": 820.0, "write_kb": 1240.0},
            "network": {"download_kb": 185.4, "upload_kb": 22.6}
        }
    }
}


def compute_category_winners(data: dict) -> Tuple[Dict[str, Dict[str, Any]], str, Dict[str, int]]:
    """
    Computes winning app for each performance dimension.
    Lower is better for startup, CPU, RAM, Jank, Net, and Disk.
    Higher is better for FPS.
    """
    apps = list(data.keys())
    if not apps:
        return {}, "None", {}

    def get_val(app: str, metric: str) -> float:
        d = data[app]
        if metric == "cold":
            return float(d["startup"]["cold_start_median_ms"])
        elif metric == "hot":
            return float(d["startup"]["hot_start_median_ms"])
        elif metric == "cpu":
            return float(d["performance"]["cpu"]["avg_percent"])
        elif metric == "ram":
            return float(d["performance"]["memory"]["avg_pss_mb"])
        elif metric == "jank":
            return float(d["performance"]["rendering"]["jank_percentage"])
        elif metric == "fps":
            return float(d["performance"]["rendering"]["approx_fps"])
        elif metric == "net_down":
            return float(d["performance"]["network"].get("download_kb", 0.0))
        elif metric == "net_up":
            return float(d["performance"]["network"].get("upload_kb", 0.0))
        elif metric == "disk_read":
            return float(d["performance"]["disk"].get("read_kb", 0.0))
        elif metric == "disk_write":
            return float(d["performance"]["disk"].get("write_kb", 0.0))
        return 0.0

    specs = {
        "cold": {"name": "Cold Startup", "unit": "ms", "better": "lower", "icon": "🚀"},
        "hot": {"name": "Hot Startup", "unit": "ms", "better": "lower", "icon": "⚡"},
        "cpu": {"name": "CPU Efficiency", "unit": "%", "better": "lower", "icon": "🔋"},
        "ram": {"name": "Memory Footprint", "unit": "MB", "better": "lower", "icon": "🧠"},
        "jank": {"name": "UI Smoothness (Lowest Jank)", "unit": "%", "better": "lower", "icon": "🧈"},
        "fps": {"name": "Frame Rate (FPS)", "unit": "FPS", "better": "higher", "icon": "🎯"},
        "net_down": {"name": "Network Download", "unit": "KB", "better": "lower", "icon": "📥"},
        "net_up": {"name": "Network Upload", "unit": "KB", "better": "lower", "icon": "📤"},
        "disk_read": {"name": "Disk Read Efficiency", "unit": "KB", "better": "lower", "icon": "📖"},
        "disk_write": {"name": "Disk Write Efficiency", "unit": "KB", "better": "lower", "icon": "💾"},
    }

    winners = {}
    win_counts = {app: 0 for app in apps}

    for metric, meta in specs.items():
        if meta["better"] == "lower":
            # For network and disk, if value is 0.0 and others are positive, check if valid
            best_app = min(apps, key=lambda a: get_val(a, metric))
        else:
            best_app = max(apps, key=lambda a: get_val(a, metric))

        val = get_val(best_app, metric)
        winners[metric] = {
            "app": best_app,
            "value": f"{val} {meta['unit']}",
            "raw_val": val,
            "name": meta["name"],
            "icon": meta["icon"]
        }
        win_counts[best_app] += 1

    champion = max(win_counts, key=win_counts.get)
    return winners, champion, win_counts


def generate_html_report(data: dict, output_filepath: str = DEFAULT_REPORT_PATH):
    app_labels = list(data.keys())
    winners, champion, win_counts = compute_category_winners(data)

    cold_starts = [data[app]["startup"]["cold_start_median_ms"] for app in app_labels]
    hot_starts = [data[app]["startup"]["hot_start_median_ms"] for app in app_labels]
    avg_cpu = [data[app]["performance"]["cpu"]["avg_percent"] for app in app_labels]
    avg_mem = [data[app]["performance"]["memory"]["avg_pss_mb"] for app in app_labels]
    jank_pct = [data[app]["performance"]["rendering"]["jank_percentage"] for app in app_labels]
    fps_val = [data[app]["performance"]["rendering"]["approx_fps"] for app in app_labels]
    
    net_down = [data[app]["performance"]["network"].get("download_kb", 0.0) for app in app_labels]
    net_up = [data[app]["performance"]["network"].get("upload_kb", 0.0) for app in app_labels]
    disk_read = [data[app]["performance"]["disk"].get("read_kb", 0.0) for app in app_labels]
    disk_write = [data[app]["performance"]["disk"].get("write_kb", 0.0) for app in app_labels]

    # Helper for cell winner badge
    def win_badge(metric: str, app: str, content: str) -> str:
        if winners.get(metric, {}).get("app") == app:
            return f"""<span class="inline-flex items-center gap-1 text-emerald-400 font-bold bg-emerald-950/70 border border-emerald-500/50 px-2 py-0.5 rounded shadow-sm">{content} <span class="text-xs">🏆</span></span>"""
        return f"""<span class="text-slate-300">{content}</span>"""

    # Generate table rows
    table_rows = ""
    for app in app_labels:
        d = data[app]
        perf = d["performance"]
        is_champ = (app == champion)
        
        table_rows += f"""
        <tr class="hover:bg-slate-800/60 transition {'bg-indigo-950/20' if is_champ else ''}">
            <td class="font-bold text-left px-4 py-3.5 border border-slate-800 text-white flex items-center justify-between">
                <span>{app}</span>
                {'<span class="px-2 py-0.5 bg-amber-500/20 border border-amber-400/50 text-amber-300 text-xs rounded-full font-bold">👑 Champion</span>' if is_champ else ''}
            </td>
            <td class="px-3 py-2 border border-slate-800">{win_badge('cold', app, f"{d['startup']['cold_start_median_ms']} ms")}</td>
            <td class="px-3 py-2 border border-slate-800">{win_badge('hot', app, f"{d['startup']['hot_start_median_ms']} ms")}</td>
            <td class="px-3 py-2 border border-slate-800">{win_badge('cpu', app, f"{perf['cpu']['avg_percent']}%")}</td>
            <td class="px-3 py-2 border border-slate-800">{win_badge('ram', app, f"{perf['memory']['avg_pss_mb']} MB")}</td>
            <td class="px-3 py-2 border border-slate-800">{win_badge('jank', app, f"{perf['rendering']['jank_percentage']}%")}</td>
            <td class="px-3 py-2 border border-slate-800">{win_badge('fps', app, f"{perf['rendering']['approx_fps']} FPS")}</td>
            <td class="px-3 py-2 border border-slate-800 bg-teal-950/10">{win_badge('net_down', app, f"{perf['network'].get('download_kb', 0.0)} KB")}</td>
            <td class="px-3 py-2 border border-slate-800 bg-cyan-950/10">{win_badge('net_up', app, f"{perf['network'].get('upload_kb', 0.0)} KB")}</td>
            <td class="px-3 py-2 border border-slate-800 bg-amber-950/10">{win_badge('disk_read', app, f"{perf['disk'].get('read_kb', 0.0)} KB")}</td>
            <td class="px-3 py-2 border border-slate-800 bg-purple-950/10">{win_badge('disk_write', app, f"{perf['disk'].get('write_kb', 0.0)} KB")}</td>
        </tr>
        """

    # Winner Cards Grid HTML
    winner_cards_html = ""
    for metric_key, meta in winners.items():
        winner_cards_html += f"""
        <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-4 flex flex-col justify-between hover:border-slate-700 transition shadow">
            <div class="flex items-center justify-between text-xs text-slate-400 font-semibold mb-2">
                <span class="flex items-center gap-1.5">{meta['icon']} {meta['name']}</span>
                <span class="px-2 py-0.5 bg-emerald-950/80 border border-emerald-500/40 text-emerald-400 rounded-md text-[10px] uppercase font-bold">Winner</span>
            </div>
            <div class="flex items-baseline justify-between mt-1">
                <span class="text-base font-extrabold text-white">{meta['app']}</span>
                <span class="text-sm font-bold text-emerald-400">{meta['value']}</span>
            </div>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mobile App Performance Benchmark Report</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ background-color: #0b0f19; color: #f8fafc; font-family: ui-sans-serif, system-ui, -apple-system, sans-serif; }}
        .card {{ background: #131b2e; border: 1px solid #1e293b; border-radius: 0.875rem; box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3); }}
    </style>
</head>
<body class="p-6 md:p-10">
    <div class="max-w-7xl mx-auto space-y-8">
        <!-- Header -->
        <div class="flex flex-col md:flex-row justify-between items-start md:items-center border-b border-slate-800 pb-6">
            <div>
                <h1 class="text-3xl font-extrabold tracking-tight text-white flex items-center gap-3">
                    <span class="w-3.5 h-8 bg-indigo-500 rounded-full inline-block"></span>
                    Mobile App Performance Benchmark
                </h1>
                <p class="text-slate-400 mt-1">Multi-App Comparative Analysis: Startup, CPU, Memory, Jank, FPS, Network & Disk I/O</p>
            </div>
            <div class="mt-4 md:mt-0 flex items-center gap-3">
                <span class="px-3.5 py-1.5 bg-emerald-950/80 border border-emerald-500/40 rounded-full text-emerald-300 text-xs font-semibold flex items-center gap-1.5">
                    <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span> Physical Device Tested
                </span>
                <span class="px-3.5 py-1.5 bg-indigo-950/80 border border-indigo-500/40 rounded-full text-indigo-300 text-xs font-semibold">
                    Mac Mini Hub Engine
                </span>
            </div>
        </div>

        <!-- Category Winners & Champion Highlight -->
        <div class="card p-6 bg-gradient-to-r from-slate-900 via-indigo-950/30 to-slate-900 border-indigo-900/50">
            <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-6 border-b border-slate-800 pb-4">
                <div>
                    <h2 class="text-xl font-extrabold text-white flex items-center gap-2">
                        <span>🏆</span> Category Winners & Scorecard
                    </h2>
                    <p class="text-xs text-slate-400 mt-0.5">Automated side-by-side performance evaluation across all 10 key telemetry dimensions</p>
                </div>
                <div class="px-4 py-2 bg-amber-500/10 border border-amber-500/30 rounded-xl flex items-center gap-2.5">
                    <span class="text-2xl">👑</span>
                    <div>
                        <div class="text-[10px] uppercase tracking-wider text-amber-400 font-bold">Overall Performance Champion</div>
                        <div class="text-base font-extrabold text-white">{champion} <span class="text-xs text-slate-400 font-normal">({win_counts.get(champion, 0)} category wins)</span></div>
                    </div>
                </div>
            </div>

            <!-- Winners Grid -->
            <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3.5">
                {winner_cards_html}
            </div>
        </div>

        <!-- Comparative Summary Table with Winner Highlights -->
        <div class="card p-6 overflow-x-auto">
            <div class="flex justify-between items-center mb-4">
                <h2 class="text-lg font-bold text-slate-100 flex items-center gap-2">
                    Executive Comparison Table
                </h2>
                <span class="text-xs text-slate-400 flex items-center gap-1.5">
                    <span class="inline-block px-1.5 py-0.2 bg-emerald-950 border border-emerald-500 text-emerald-400 rounded text-[10px] font-bold">🏆</span> indicates the winning app for that specific metric
                </span>
            </div>
            <table class="w-full text-center text-sm border-collapse border border-slate-800">
                <thead>
                    <tr class="bg-slate-900/90 text-slate-400 uppercase text-xs tracking-wider">
                        <th class="px-4 py-3.5 border border-slate-800 text-left">App Label</th>
                        <th class="px-3 py-3.5 border border-slate-800">Cold Start</th>
                        <th class="px-3 py-3.5 border border-slate-800">Hot Start</th>
                        <th class="px-3 py-3.5 border border-slate-800">Avg CPU</th>
                        <th class="px-3 py-3.5 border border-slate-800">RAM (PSS)</th>
                        <th class="px-3 py-3.5 border border-slate-800">Jank Rate</th>
                        <th class="px-3 py-3.5 border border-slate-800">FPS</th>
                        <th class="px-3 py-3.5 border border-slate-800 text-teal-400 bg-teal-950/20">Net Down</th>
                        <th class="px-3 py-3.5 border border-slate-800 text-cyan-400 bg-cyan-950/20">Net Up</th>
                        <th class="px-3 py-3.5 border border-slate-800 text-amber-400 bg-amber-950/20">Disk Read</th>
                        <th class="px-3 py-3.5 border border-slate-800 text-purple-400 bg-purple-950/20">Disk Write</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-slate-800 text-slate-200">
                    {table_rows}
                </tbody>
            </table>
        </div>

        <!-- Charts Grid (2 Columns, 5 Charts) -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <!-- Chart 1: Startup Latency -->
            <div class="card p-6">
                <div class="flex justify-between items-center mb-1">
                    <h3 class="text-base font-bold text-slate-100 flex items-center gap-2">
                        <span>🚀</span> 1. Startup Latency
                    </h3>
                    <span class="text-xs text-indigo-400 font-medium">Lower is Better (ms)</span>
                </div>
                <p class="text-xs text-slate-400 mb-4">Cold Process Initialization vs Warm/Hot Foreground Resume</p>
                <div class="h-64"><canvas id="startupChart"></canvas></div>
            </div>

            <!-- Chart 2: CPU & Memory -->
            <div class="card p-6">
                <div class="flex justify-between items-center mb-1">
                    <h3 class="text-base font-bold text-slate-100 flex items-center gap-2">
                        <span>🔋</span> 2. Resource Consumption
                    </h3>
                    <span class="text-xs text-pink-400 font-medium">Lower is Better</span>
                </div>
                <p class="text-xs text-slate-400 mb-4">Average CPU Utilization (%) vs Memory Footprint (PSS MB)</p>
                <div class="h-64"><canvas id="resourceChart"></canvas></div>
            </div>

            <!-- Chart 3: Jank & FPS -->
            <div class="card p-6">
                <div class="flex justify-between items-center mb-1">
                    <h3 class="text-base font-bold text-slate-100 flex items-center gap-2">
                        <span>🧈</span> 3. UI Smoothness & FPS
                    </h3>
                    <span class="text-xs text-emerald-400 font-medium">Target 60 FPS</span>
                </div>
                <p class="text-xs text-slate-400 mb-4">Jank % (Lower is better) vs Effective Rendering FPS (Higher is better)</p>
                <div class="h-64"><canvas id="renderingChart"></canvas></div>
            </div>

            <!-- Chart 4: Network Download vs Upload -->
            <div class="card p-6">
                <div class="flex justify-between items-center mb-1">
                    <h3 class="text-base font-bold text-slate-100 flex items-center gap-2">
                        <span>🌐</span> 4. Network Data Transfer
                    </h3>
                    <span class="text-xs text-teal-400 font-medium">Lower is Better (KB)</span>
                </div>
                <p class="text-xs text-slate-400 mb-4">Separated Network Download (Rx) vs Upload (Tx) Payload Size</p>
                <div class="h-64"><canvas id="networkChart"></canvas></div>
            </div>

            <!-- Chart 5: Disk Read vs Write -->
            <div class="card p-6 md:col-span-2">
                <div class="flex justify-between items-center mb-1">
                    <h3 class="text-base font-bold text-slate-100 flex items-center gap-2">
                        <span>💾</span> 5. Disk Storage I/O
                    </h3>
                    <span class="text-xs text-amber-400 font-medium">Lower is Better (KB)</span>
                </div>
                <p class="text-xs text-slate-400 mb-4">Separated Block Storage Read Operations vs Cache/Database Writes</p>
                <div class="h-64"><canvas id="diskChart"></canvas></div>
            </div>
        </div>
    </div>

    <script>
        const labels = {json.dumps(app_labels)};

        // 1. Startup Chart
        new Chart(document.getElementById('startupChart'), {{
            type: 'bar',
            data: {{
                labels: labels,
                datasets: [
                    {{ label: 'Cold Start (ms)', data: {json.dumps(cold_starts)}, backgroundColor: '#6366f1' }},
                    {{ label: 'Hot Start (ms)', data: {json.dumps(hot_starts)}, backgroundColor: '#38bdf8' }}
                ]
            }},
            options: {{ responsive: true, maintainAspectRatio: false, scales: {{ y: {{ grid: {{ color: '#1e293b' }} }} }} }}
        }});

        // 2. Resource Chart
        new Chart(document.getElementById('resourceChart'), {{
            type: 'bar',
            data: {{
                labels: labels,
                datasets: [
                    {{ label: 'Avg CPU %', data: {json.dumps(avg_cpu)}, backgroundColor: '#f59e0b' }},
                    {{ label: 'Avg RAM PSS (MB)', data: {json.dumps(avg_mem)}, backgroundColor: '#ec4899' }}
                ]
            }},
            options: {{ responsive: true, maintainAspectRatio: false, scales: {{ y: {{ grid: {{ color: '#1e293b' }} }} }} }}
        }});

        // 3. Rendering Chart
        new Chart(document.getElementById('renderingChart'), {{
            type: 'bar',
            data: {{
                labels: labels,
                datasets: [
                    {{ label: 'Jank %', data: {json.dumps(jank_pct)}, backgroundColor: '#f43f5e' }},
                    {{ label: 'FPS', data: {json.dumps(fps_val)}, backgroundColor: '#10b981' }}
                ]
            }},
            options: {{ responsive: true, maintainAspectRatio: false, scales: {{ y: {{ grid: {{ color: '#1e293b' }} }} }} }}
        }});

        // 4. Network Chart (Download vs Upload)
        new Chart(document.getElementById('networkChart'), {{
            type: 'bar',
            data: {{
                labels: labels,
                datasets: [
                    {{ label: 'Download (KB)', data: {json.dumps(net_down)}, backgroundColor: '#14b8a6' }},
                    {{ label: 'Upload (KB)', data: {json.dumps(net_up)}, backgroundColor: '#06b6d4' }}
                ]
            }},
            options: {{ responsive: true, maintainAspectRatio: false, scales: {{ y: {{ grid: {{ color: '#1e293b' }} }} }} }}
        }});

        // 5. Disk Chart (Read vs Write)
        new Chart(document.getElementById('diskChart'), {{
            type: 'bar',
            data: {{
                labels: labels,
                datasets: [
                    {{ label: 'Disk Read (KB)', data: {json.dumps(disk_read)}, backgroundColor: '#f59e0b' }},
                    {{ label: 'Disk Write (KB)', data: {json.dumps(disk_write)}, backgroundColor: '#a855f7' }}
                ]
            }},
            options: {{ responsive: true, maintainAspectRatio: false, scales: {{ y: {{ grid: {{ color: '#1e293b' }} }} }} }}
        }});
    </script>
</body>
</html>
"""
    with open(output_filepath, "w") as f:
        f.write(html)
    print(f"[+] HTML Report generated at: {output_filepath}")


if __name__ == "__main__":
    data_file = sys.argv[1] if len(sys.argv) > 1 else os.path.join(SCRIPT_DIR, "benchmark_results.json")
    if os.path.exists(data_file):
        with open(data_file, "r") as f:
            data = json.load(f)
    else:
        print("[*] No custom json provided, rendering with sample benchmark dataset...")
        data = SAMPLE_BENCHMARK_DATA

    generate_html_report(data)
