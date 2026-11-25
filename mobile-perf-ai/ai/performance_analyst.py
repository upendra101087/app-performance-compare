"""
AI Performance Analyst.
Generates automated Root Cause Analysis (RCA) and architectural recommendations
from Phase-Segmented benchmark telemetry.
"""

import json
import os
import re
import urllib.request
from typing import Dict, Any, Optional

from ai.prompt_templates import PERFORMANCE_RCA_PROMPT


class PerformanceAnalyst:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")

    def generate_rca(self, benchmark_data: Dict[str, Any]) -> str:
        """
        Analyzes comparative benchmark metrics and returns an in-depth diagnosis.
        """
        app_names = ", ".join(benchmark_data.keys())
        
        # 1. Attempt LLM Generation if API key is configured
        if self.api_key and os.getenv("GEMINI_API_KEY"):
            llm_report = self._call_gemini_api(benchmark_data, app_names)
            if llm_report:
                return llm_report

        # 2. Built-in Expert Rule-Based Diagnostic Engine (Fallback)
        return self._generate_heuristic_rca(benchmark_data)

    def _call_gemini_api(self, data: Dict[str, Any], app_names: str) -> Optional[str]:
        prompt = PERFORMANCE_RCA_PROMPT.format(
            app_names=app_names,
            benchmark_metrics_json=json.dumps(data, indent=2)
        )
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={os.getenv('GEMINI_API_KEY')}"
            payload = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                res_data = json.loads(resp.read().decode())
                return res_data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            print(f"[-] [AI Analyst] Gemini API query failed: {e}. Using built-in analyst engine...")
            return None

    def _generate_heuristic_rca(self, data: Dict[str, Any]) -> str:
        """
        Built-in heuristic analysis when offline or running without LLM tokens.
        """
        lines = []
        lines.append("### 🤖 Automated AI Performance Root Cause Analysis (RCA)\n")
        
        apps = list(data.keys())
        if not apps:
            return "No application data available for analysis."

        # 1. Startup Analysis
        lines.append("#### 1. Cold Launch & Startup Pipeline")
        for app in apps:
            startup = data[app].get("startup", {})
            cold = startup.get("cold_start_to_mpin_ms")
            hot = startup.get("hot_resume_ms")
            lines.append(f"- **{app}**: Cold to MPIN: `{cold if cold else 'N/A'} ms` | Hot Resume: `{hot if hot else 'N/A'} ms`")
        
        cold_valid = {a: data[a]["startup"].get("cold_start_to_mpin_ms") for a in apps if data[a]["startup"].get("cold_start_to_mpin_ms")}
        if cold_valid:
            fastest_cold = min(cold_valid, key=cold_valid.get)
            lines.append(f"\n> **Startup Finding**: **{fastest_cold}** exhibited the lowest process initialization latency. Applications with cold times > 800ms typically suffer from synchronous Application.onCreate() SDK initialization (e.g. Firebase, Crashlytics, Ad/Analytics trackers) rather than using Jetpack App Startup deferred initializers.")

        # 2. Rendering & Jank Analysis
        lines.append("\n#### 2. Frame Presentation & UI Jank Diagnosis")
        for app in apps:
            phases = data[app].get("phases", {})
            for phase_name, p in phases.items():
                jank = p.get("jank_percentage", 0.0)
                fps = p.get("approx_fps", 60.0)
                p95 = p.get("p95_frame_time_ms", 16.0)
                if jank > 5.0 or p95 > 20.0:
                    lines.append(f"- ⚠️ **{app} ({phase_name})**: High Jank Rate `{jank}%` (Effective FPS: `{fps}`, p95 frame time: `{p95}ms`). Root cause likely involves layout thrashing, uncompressed image decodes on the main thread, or un-recycled view items during scroll velocity peaks.")
                else:
                    lines.append(f"- ✅ **{app} ({phase_name})**: Smooth rendering (`{jank}%` jank, `{fps}` FPS, p95: `{p95}ms`).")

        # 3. Memory & Leaks
        lines.append("\n#### 3. Memory & Resource Footprint")
        for app in apps:
            phases = data[app].get("phases", {})
            pss_list = [p.get("avg_pss_mb", 0.0) for p in phases.values() if p.get("avg_pss_mb", 0.0) > 0]
            max_pss = max(pss_list) if pss_list else 0.0
            lines.append(f"- **{app}**: Peak PSS Allocation: `{max_pss} MB`")
            if max_pss > 350.0:
                lines.append(f"  - ⚠️ High memory footprint detected. Watch for uncapped bitmap LRU caches and unbounded websocket event queues.")

        # 4. Actionable Optimizations
        lines.append("\n#### 4. Actionable Engineering Recommendations")
        lines.append("1. **Vsync Deadline Adherence**: Optimize heavy RecyclerView/LazyColumn items by using ViewBinding without redundant findViewById lookups or pre-computing text layouts via PrecomputedTextCompat.")
        lines.append("2. **Deferred Initialization**: Migrate analytics and third-party tracking from `Application.onCreate()` to background coroutines via Android Jetpack `androidx.startup`.")
        lines.append("3. **Chart Multi-Touch Throttling**: Throttle websocket quote dispatchers while multi-touch pinch gestures are active on candlestick charts to prevent RenderThread starvation.")

        return "\n".join(lines)
