"""
HTML Report Generator for Phase-Segmented Mobile Performance Benchmarks.
Produces an executive dashboard with category winners, phase breakdowns, and AI RCA.
"""

import json
import os
from typing import Dict, Any


def generate_html_report(benchmark_data: Dict[str, Any], output_filepath: str = "performance_benchmark_report.html"):
    apps = list(benchmark_data.keys())
    
    # 1. Compute Category Winners
    winners = {}
    
    # Startup Winner
    cold_starts = {a: benchmark_data[a].get("startup", {}).get("cold_start_to_mpin_ms") for a in apps if benchmark_data[a].get("startup", {}).get("cold_start_to_mpin_ms")}
    if cold_starts:
        best_cold = min(cold_starts, key=cold_starts.get)
        winners["Cold Start"] = f"{best_cold} ({cold_starts[best_cold]} ms)"
        
    hot_starts = {a: benchmark_data[a].get("startup", {}).get("hot_resume_ms") for a in apps if benchmark_data[a].get("startup", {}).get("hot_resume_ms")}
    if hot_starts:
        best_hot = min(hot_starts, key=hot_starts.get)
        winners["Hot Resume"] = f"{best_hot} ({hot_starts[best_hot]} ms)"

    # Compute overall jank winner across all phases
    avg_janks = {}
    avg_fpss = {}
    avg_rams = {}
    for a in apps:
        phases = benchmark_data[a].get("phases", {})
        if phases:
            j_vals = [p.get("jank_percentage", 0.0) for p in phases.values()]
            f_vals = [p.get("approx_fps", 60.0) for p in phases.values()]
            r_vals = [p.get("avg_pss_mb", 0.0) for p in phases.values()]
            avg_janks[a] = round(sum(j_vals) / len(j_vals), 1) if j_vals else 0.0
            avg_fpss[a] = round(sum(f_vals) / len(f_vals), 1) if f_vals else 60.0
            avg_rams[a] = round(sum(r_vals) / len(r_vals), 1) if r_vals else 0.0

    if avg_janks:
        best_jank = min(avg_janks, key=avg_janks.get)
        winners["UI Smoothness"] = f"{best_jank} ({avg_janks[best_jank]}% avg jank)"
    if avg_fpss:
        best_fps = max(avg_fpss, key=avg_fpss.get)
        winners["Frame Rate"] = f"{best_fps} ({avg_fpss[best_fps]} FPS)"
    if avg_rams:
        best_ram = min(avg_rams, key=avg_rams.get)
        winners["RAM Efficiency"] = f"{best_ram} ({avg_rams[best_ram]} MB avg)"

    # 2. Extract Phase List
    all_phases = []
    for a in apps:
        for p in benchmark_data[a].get("phases", {}).keys():
            if p not in all_phases:
                all_phases.append(p)

    # 3. Build HTML Table Rows
    phase_rows = ""
    for phase in all_phases:
        phase_rows += f"<tr class='phase-header'><td colspan='{len(apps) * 4 + 1}'><strong>📌 {phase.replace('_', ' ').title()}</strong></td></tr>\n"
        phase_rows += "<tr><td>Metrics</td>"
        for a in apps:
            phase_rows += f"<td><strong>{a} Jank %</strong></td><td><strong>{a} FPS</strong></td><td><strong>{a} CPU %</strong></td><td><strong>{a} RAM (MB)</strong></td>"
        phase_rows += "</tr>\n<tr><td>Values</td>"
        for a in apps:
            p_data = benchmark_data[a].get("phases", {}).get(phase, {})
            jank = p_data.get("jank_percentage", "-")
            fps = p_data.get("approx_fps", "-")
            cpu = p_data.get("avg_cpu_percent", "-")
            ram = p_data.get("avg_pss_mb", "-")
            
            jank_color = "green" if isinstance(jank, (int, float)) and jank <= 3.0 else "orange" if isinstance(jank, (int, float)) and jank <= 7.0 else "red"
            phase_rows += f"<td style='color:{jank_color}'><strong>{jank}%</strong></td><td>{fps}</td><td>{cpu}%</td><td>{ram} MB</td>"
        phase_rows += "</tr>\n"

    # AI RCA
    ai_rca = benchmark_data.get("_meta", {}).get("ai_rca") or benchmark_data.get(apps[0], {}).get("ai_root_cause_analysis", "AI RCA generated during run.")

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Mobile Performance Benchmarking Report (AI-Powered)</title>
<style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 24px; }}
    .container {{ max-width: 1200px; margin: 0 auto; }}
    .header {{ text-align: center; margin-bottom: 30px; }}
    .header h1 {{ margin: 0; color: #38bdf8; font-size: 28px; }}
    .header p {{ color: #94a3b8; font-size: 14px; margin-top: 6px; }}
    
    .winner-cards {{ display: flex; gap: 16px; margin-bottom: 24px; flex-wrap: wrap; }}
    .card {{ background: #1e293b; border-radius: 12px; padding: 16px 20px; flex: 1; min-width: 200px; border: 1px solid #334155; }}
    .card h3 {{ margin: 0 0 6px 0; font-size: 13px; color: #94a3b8; text-transform: uppercase; }}
    .card .val {{ font-size: 18px; font-weight: bold; color: #10b981; }}
    
    .table-container {{ background: #1e293b; border-radius: 12px; padding: 20px; margin-bottom: 24px; overflow-x: auto; border: 1px solid #334155; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ padding: 12px 14px; text-align: left; border-bottom: 1px solid #334155; }}
    th {{ background: #0f172a; color: #38bdf8; }}
    tr.phase-header td {{ background: #0f172a; color: #f59e0b; padding-top: 18px; font-size: 15px; border-bottom: 2px solid #334155; }}
    
    .ai-box {{ background: #1e1b4b; border-left: 4px solid #818cf8; border-radius: 12px; padding: 24px; margin-bottom: 24px; border: 1px solid #312e81; }}
    .ai-box h2 {{ margin: 0 0 12px 0; color: #c7d2fe; font-size: 20px; }}
    .ai-box pre {{ white-space: pre-wrap; font-family: inherit; color: #e0e7ff; line-height: 1.6; font-size: 14px; margin: 0; }}
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>📊 Mobile Performance Benchmark Report</h1>
        <p>Phase-Segmented Telemetry across Target Trading Applications</p>
    </div>

    <!-- Category Highlights -->
    <div class="winner-cards">
        {''.join([f'<div class="card"><h3>🏆 {cat}</h3><div class="val">{val}</div></div>' for cat, val in winners.items()])}
    </div>

    <!-- AI RCA Section -->
    <div class="ai-box">
        <h2>🧠 AI Performance Root Cause Analysis (RCA)</h2>
        <pre>{ai_rca}</pre>
    </div>

    <!-- Phase by Phase Table -->
    <div class="table-container">
        <h2>📋 Phase-Segmented Breakdown</h2>
        <table>
            <tbody>
                {phase_rows}
            </tbody>
        </table>
    </div>
</div>
</body>
</html>
"""

    with open(output_filepath, "w") as f:
        f.write(html_content)
    print(f"\n[+] Visual Performance Dashboard generated at: file://{os.path.abspath(output_filepath)}")
