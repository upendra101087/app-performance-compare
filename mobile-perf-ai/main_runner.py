#!/usr/bin/env python3
"""
Master Orchestrator for Phase-Segmented Mobile Performance Benchmarking.
Executes multi-screen user journeys across Target vs Competitor FinTech apps
(Cold/Hot Start, Homepage 10x Scroll, Watchlist, Portfolio, Positions, Chart Pinch-Zoom)
with integrated AI Self-Healing and Automated Root Cause Analysis (RCA).
"""

import argparse
import json
import os
import subprocess
import sys
import time
from typing import Dict, Any, List, Optional

from telemetry.android_collector import AndroidTelemetryCollector
from telemetry.models import AppBenchmarkReport, StartupMetrics
from core.driver_factory import DriverFactory
from core.gesture_engine import GestureEngine
from core.phase_tracker import PhaseTracker
from pages import GrowwPage, AngelOnePage, DhanPage, SahiPage
from ai.self_healing_agent import SelfHealingAgent
from ai.performance_analyst import PerformanceAnalyst
from reporting.html_generator import generate_html_report


PAGE_REGISTRY = {
    "Groww": GrowwPage,
    "com.nextbillion.groww": GrowwPage,
    "AngelOne": AngelOnePage,
    "com.msf.angelmobile": AngelOnePage,
    "Dhan": DhanPage,
    "com.dhan.live": DhanPage,
    "Sahi": SahiPage,
    "com.sahi.app": SahiPage
}


def auto_detect_android_device() -> str:
    """Detects the first connected authorized device from adb devices."""
    try:
        res = subprocess.run(["adb", "devices"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        for line in res.stdout.strip().splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device":
                return parts[0]
    except Exception as e:
        print(f"[-] adb query failed: {e}")
    return ""


class MobilePerfMasterRunner:
    def __init__(self, config: Dict[str, Any], device_override: Optional[str] = None):
        self.config = config
        self.device_udid = device_override or config.get("device_udid", "auto")
        if self.device_udid == "auto" or not self.device_udid:
            detected = auto_detect_android_device()
            if not detected:
                print("[-] Error: No Android device detected via 'adb devices'.")
                print("    Please connect a device via USB with USB Debugging enabled.")
                sys.exit(1)
            self.device_udid = detected
            print(f"[+] Active Android Device: {self.device_udid}")

        self.hub_url = config.get("hub_url", "http://127.0.0.1:31337/wd/hub")
        self.apps = config.get("apps", [])
        self.settings = config.get("settings", {})
        
        self.ai_agent = SelfHealingAgent() if self.settings.get("use_ai_self_healing", True) else None
        self.analyst = PerformanceAnalyst() if self.settings.get("use_ai_analyst", True) else None

    def execute_app_benchmark(self, app_cfg: Dict[str, Any]) -> Optional[AppBenchmarkReport]:
        label = app_cfg.get("label", "App")
        pkg = app_cfg.get("package_name")
        mpin = app_cfg.get("mpin", "1234")

        print("\n" + "="*70)
        print(f"🚀 BENCHMARKING APP: {label} ({pkg})")
        print("="*70)

        collector = AndroidTelemetryCollector(device_udid=self.device_udid, package_name=pkg)
        tracker = PhaseTracker(collector=collector)
        screen_size = collector.get_screen_size()

        # Check installation
        pm_out = collector.run_adb(["shell", "pm", "path", pkg])
        if "package:" not in pm_out:
            print(f"[-] WARNING: Package '{pkg}' is NOT installed on device '{self.device_udid}'.")
            print(f"    Skipping '{label}' benchmark...\n")
            return None

        # 1. Driver & Page Object Setup
        driver = None
        if DriverFactory.is_appium_available():
            try:
                print(f"[*] Initializing Appium session for {label} on {self.hub_url}...")
                driver = DriverFactory.create_driver(
                    device_udid=self.device_udid,
                    package_name=pkg,
                    hub_url=self.hub_url
                )
                print(f"[+] Appium session established.")
            except Exception as e:
                print(f"[-] Appium connection failed ({e}). Running in calibrated ADB gesture mode.")

        gestures = GestureEngine(driver=driver, device_udid=self.device_udid, screen_size=screen_size)
        
        page_cls = PAGE_REGISTRY.get(label) or PAGE_REGISTRY.get(pkg) or GrowwPage
        page = page_cls(driver=driver, gesture_engine=gestures, ai_agent=self.ai_agent)

        report = AppBenchmarkReport(app_label=label, package_name=pkg)

        try:
            # ==========================
            # Phase 1: Cold Start to MPIN
            # ==========================
            print("\n[*] ─── Startup Phase: Cold Start to MPIN ───")
            cold_ms = collector.measure_cold_start_to_mpin()
            if cold_ms:
                report.startup.cold_start_to_mpin_ms = cold_ms
                print(f"[✓] Cold Launch to MPIN: {cold_ms} ms")
            else:
                print(f"[-] Cold start measurement failed to resolve TotalTime.")

            # ==========================
            # Phase 2: Enter MPIN & Unlock
            # ==========================
            time.sleep(1.0)
            t_unlock0 = time.time()
            page.enter_mpin(mpin)
            report.startup.mpin_to_dashboard_ms = int((time.time() - t_unlock0) * 1000)
            time.sleep(2.5)  # Let home screen settle

            # ==========================
            # Phase 3: Hot Resume Latency
            # ==========================
            print("\n[*] ─── Startup Phase: Hot Resume (from Background) ───")
            hot_ms = collector.measure_hot_resume(bg_dwell_sec=self.settings.get("hot_resume_dwell_sec", 2.0))
            if hot_ms:
                report.startup.hot_resume_ms = hot_ms
                print(f"[✓] Hot Resume Latency: {hot_ms} ms")

            # ==========================
            # Phase 4: Homepage 10x Scroll
            # ==========================
            scrolls = self.settings.get("scroll_iterations", 10)
            report.phases["homepage_10x_scroll"] = tracker.profile_phase(
                "Homepage 10x Scroll",
                lambda: page.scroll_homepage(times=scrolls)
            )

            # ==========================
            # Phase 5: Watchlist 10x Scroll
            # ==========================
            page.navigate_to_watchlist()
            report.phases["watchlist_10x_scroll"] = tracker.profile_phase(
                "Watchlist 10x Scroll",
                lambda: page.scroll_watchlist(times=scrolls)
            )

            # ==========================
            # Phase 6: Portfolio 10x Scroll
            # ==========================
            page.navigate_to_portfolio()
            report.phases["portfolio_10x_scroll"] = tracker.profile_phase(
                "Portfolio 10x Scroll",
                lambda: page.scroll_portfolio(times=scrolls)
            )

            # ==========================
            # Phase 7: Positions 10x Scroll
            # ==========================
            page.navigate_to_positions()
            report.phases["positions_10x_scroll"] = tracker.profile_phase(
                "Positions 10x Scroll",
                lambda: page.scroll_positions(times=scrolls)
            )

            # ==========================
            # Phase 8: Candlestick Chart Pinch Zoom
            # ==========================
            page.open_chart()
            pinch_cycles = self.settings.get("chart_pinch_cycles", 5)
            report.phases["chart_pinch_zoom"] = tracker.profile_phase(
                "Chart Pinch Zoom",
                lambda: page.pinch_zoom_chart(cycles=pinch_cycles)
            )

        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

        return report

    def run_all(self, output_json: str = "benchmark_results.json", output_html: str = "performance_benchmark_report.html"):
        final_results = {}

        for app_cfg in self.apps:
            if not app_cfg.get("enabled", True):
                continue
            rep = self.execute_app_benchmark(app_cfg)
            if rep:
                final_results[rep.app_label] = rep.to_dict()
            time.sleep(3.0)  # Cool down between app test suites

        if not final_results:
            print("[-] No benchmark data collected.")
            return

        # AI RCA Generation
        if self.analyst:
            print("\n" + "="*70)
            print("🧠 RUNNING AI PERFORMANCE ANALYST (ROOT CAUSE ANALYSIS)...")
            print("="*70)
            rca = self.analyst.generate_rca(final_results)
            final_results["_meta"] = {"ai_rca": rca}
            print(rca)

        # Write JSON output
        with open(output_json, "w") as f:
            json.dump(final_results, f, indent=2)
        print(f"\n[+] Raw telemetry data saved to: {output_json}")

        # Write HTML Dashboard
        generate_html_report(final_results, output_filepath=output_html)


def main():
    parser = argparse.ArgumentParser(description="Mobile Performance Benchmarking Suite (AI-Powered)")
    parser.add_argument("--config", default="config/benchmark_config.json", help="Path to benchmark_config.json")
    parser.add_argument("--device", help="Device UDID override")
    parser.add_argument("--output-json", default="benchmark_results.json")
    parser.add_argument("--output-html", default="performance_benchmark_report.html")
    args = parser.parse_args()

    cfg_path = args.config
    if not os.path.exists(cfg_path):
        # Fallback to local config
        cfg_path = os.path.join(os.path.dirname(__file__), "config", "benchmark_config.json")

    with open(cfg_path, "r") as f:
        config = json.load(f)

    runner = MobilePerfMasterRunner(config=config, device_override=args.device)
    runner.run_all(output_json=args.output_json, output_html=args.output_html)


if __name__ == "__main__":
    main()
