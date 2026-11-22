#!/usr/bin/env python3
"""
Benchmark Orchestrator for Mobile App Performance
Executes standardized performance test scenarios across Target App vs Competitor Apps.
Runs on physical devices managed locally or via the Mac Mini Device Farm.

Usage:
    python3 benchmark_orchestrator.py                     # Runs with default benchmark_config.json
    python3 benchmark_orchestrator.py --config custom.json # Runs with custom config file
    python3 benchmark_orchestrator.py --device <UDID>      # Explicitly specify target device
"""

import argparse
import json
import os
import subprocess
import sys
import time
from typing import Dict, Any, List, Optional
from android_perf_collector import AndroidPerfCollector
from generate_comparison_report import generate_html_report


def auto_detect_android_device() -> str:
    """Detects the first connected and authorized Android device from adb devices."""
    try:
        res = subprocess.run(["adb", "devices"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        lines = res.stdout.strip().splitlines()
        devices = []
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device":
                devices.append(parts[0])
        if devices:
            print(f"[+] Auto-detected connected Android device: {devices[0]}")
            return devices[0]
    except Exception as e:
        print(f"[-] Failed to query adb devices: {e}")
    return ""


class BenchmarkOrchestrator:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.device_udid = config.get("device_udid", "auto")
        if self.device_udid == "auto" or not self.device_udid:
            detected = auto_detect_android_device()
            if not detected:
                print("[-] Error: No active Android device detected via 'adb devices'.")
                print("    Ensure your device is connected via USB with USB Debugging enabled.")
                sys.exit(1)
            self.device_udid = detected

        self.iterations = int(config.get("iterations", 3))
        self.scenario_duration = int(config.get("scenario_duration_sec", 15))
        self.apps = config.get("apps", [])

    def run_cold_start(self, collector: AndroidPerfCollector, label: str) -> List[int]:
        cold_times = []
        print(f"\n[*] Measuring Cold Start for {label} ({self.iterations} iterations)...")
        for i in range(self.iterations):
            data = collector.measure_cold_startup()
            t = data.get("cold_total_time_ms")
            if t:
                cold_times.append(t)
                print(f"    Iteration {i+1}: {t} ms")
            else:
                err = data.get("error", "Unable to resolve launcher intent or start app.")
                print(f"    Iteration {i+1}: Failed to launch. Details: {err}")
            time.sleep(2.0)
        return cold_times

    def run_hot_start(self, collector: AndroidPerfCollector, label: str) -> List[int]:
        hot_times = []
        print(f"[*] Measuring Hot Start for {label} ({self.iterations} iterations)...")
        for i in range(self.iterations):
            data = collector.measure_hot_startup()
            t = data.get("hot_total_time_ms")
            if t:
                hot_times.append(t)
                print(f"    Iteration {i+1}: {t} ms")
            time.sleep(2.0)
        return hot_times

    def run_interactive_workflow(self, collector: AndroidPerfCollector) -> Dict[str, Any]:
        print(f"[*] Running Interactive Scenario ({self.scenario_duration}s continuous scrolling & profiling)...")
        
        # Ensure fresh launch and settle
        collector.measure_cold_startup()
        time.sleep(2.5)

        # Start continuous profiling (resets gfxinfo and records baseline disk/network)
        collector.start_profiling()

        # Dynamically calculate centered swipe coordinates based on actual screen resolution
        width, height = collector.get_screen_size()
        center_x = width // 2
        swipe_start_y = int(height * 0.75)
        swipe_end_y = int(height * 0.25)

        start_time = time.time()
        while time.time() - start_time < self.scenario_duration:
            # Vertical scroll gesture tailored to phone resolution
            collector._run_adb([
                "shell", "input", "swipe",
                str(center_x), str(swipe_start_y),
                str(center_x), str(swipe_end_y),
                "350"
            ])
            time.sleep(0.6)

        metrics = collector.stop_profiling()
        return metrics

    def execute(self, output_json: str = "benchmark_results.json", output_html: str = "performance_benchmark_report.html"):
        print("\n" + "="*60)
        print(f" STARTING BENCHMARK ON DEVICE: {self.device_udid}")
        print("="*60)

        final_report = {}

        for app in self.apps:
            label = app["label"]
            pkg = app["package_name"]
            activity = app.get("main_activity")

            print(f"\n>>> BENCHMARKING APP: {label} ({pkg})")
            collector = AndroidPerfCollector(
                device_udid=self.device_udid,
                package_name=pkg,
                main_activity=activity
            )

            # Pre-flight Check: Is the app installed?
            if not collector.is_app_installed():
                print(f"[-] WARNING: Package '{pkg}' is NOT installed on device '{self.device_udid}'.")
                print(f"    Please install '{label}' from Google Play Store or via 'adb install <apk>'.")
                print("    Skipping this app for now...\n")
                continue

            # Auto-resolve launcher if not provided or to verify
            resolved = collector.resolve_launcher_activity()
            if resolved:
                print(f"[+] Detected Launcher Activity: {resolved}")

            # 1. Cold Start
            cold_runs = self.run_cold_start(collector, label)
            median_cold = sorted(cold_runs)[len(cold_runs)//2] if cold_runs else 0

            # 2. Hot Start
            hot_runs = self.run_hot_start(collector, label)
            median_hot = sorted(hot_runs)[len(hot_runs)//2] if hot_runs else 0

            # 3. Interactive Scenario
            perf_data = self.run_interactive_workflow(collector)

            final_report[label] = {
                "package": pkg,
                "startup": {
                    "cold_start_runs_ms": cold_runs,
                    "cold_start_median_ms": median_cold,
                    "hot_start_runs_ms": hot_runs,
                    "hot_start_median_ms": median_hot
                },
                "performance": perf_data
            }

            # Cool down before testing next app
            print("[*] Cooling down 5s before next app run...")
            time.sleep(5.0)

        if not final_report:
            print("\n[-] No test results collected. Please make sure the configured apps are installed on your device.")
            return

        # Save JSON output
        with open(output_json, "w") as f:
            json.dump(final_report, f, indent=2)
        print(f"\n[+] Raw telemetry data saved to: {output_json}")

        # Generate HTML report
        generate_html_report(final_report, output_filepath=output_html)

        # Print Console Summary Table
        self.print_summary_table(final_report)

    def print_summary_table(self, data: Dict[str, Any]):
        print("\n" + "="*132)
        print(f"{'App Label':<14} | {'Cold (ms)':<9} | {'Hot (ms)':<8} | {'Avg CPU':<8} | {'Avg RAM':<10} | {'Jank %':<7} | {'FPS':<6} | {'Net Down':<9} | {'Net Up':<8} | {'Disk Rd':<8} | {'Disk Wr':<8}")
        print("="*132)
        for label, d in data.items():
            cold = f"{d['startup']['cold_start_median_ms']} ms"
            hot = f"{d['startup']['hot_start_median_ms']} ms"
            cpu = f"{d['performance']['cpu']['avg_percent']}%"
            ram = f"{d['performance']['memory']['avg_pss_mb']} MB"
            jank = f"{d['performance']['rendering']['jank_percentage']}%"
            fps = f"{d['performance']['rendering']['approx_fps']}"
            net_down = f"{d['performance']['network'].get('download_kb', 0.0)} KB"
            net_up = f"{d['performance']['network'].get('upload_kb', 0.0)} KB"
            disk_rd = f"{d['performance']['disk'].get('read_kb', 0.0)} KB"
            disk_wr = f"{d['performance']['disk'].get('write_kb', 0.0)} KB"
            print(f"{label:<14} | {cold:<9} | {hot:<8} | {cpu:<8} | {ram:<10} | {jank:<7} | {fps:<6} | {net_down:<9} | {net_up:<8} | {disk_rd:<8} | {disk_wr:<8}")
        print("="*132)

        # Print Category Winners
        apps = list(data.keys())
        if len(apps) >= 2:
            print("\n" + "─"*55)
            print("  🏆 CATEGORY WINNERS & PERFORMANCE HIGHLIGHTS")
            print("─"*55)
            # Cold
            best_cold = min(apps, key=lambda a: data[a]["startup"]["cold_start_median_ms"])
            print(f"  🚀 Fastest Cold Start    : {best_cold} ({data[best_cold]['startup']['cold_start_median_ms']} ms)")
            # Hot
            best_hot = min(apps, key=lambda a: data[a]["startup"]["hot_start_median_ms"])
            print(f"  ⚡ Fastest Hot Start     : {best_hot} ({data[best_hot]['startup']['hot_start_median_ms']} ms)")
            # CPU
            best_cpu = min(apps, key=lambda a: data[a]["performance"]["cpu"]["avg_percent"])
            print(f"  🔋 Best CPU Efficiency   : {best_cpu} ({data[best_cpu]['performance']['cpu']['avg_percent']}%)")
            # RAM
            best_ram = min(apps, key=lambda a: data[a]["performance"]["memory"]["avg_pss_mb"])
            print(f"  🧠 Lowest RAM Footprint  : {best_ram} ({data[best_ram]['performance']['memory']['avg_pss_mb']} MB)")
            # Jank
            best_jank = min(apps, key=lambda a: data[a]["performance"]["rendering"]["jank_percentage"])
            print(f"  🧈 Lowest UI Jank Rate   : {best_jank} ({data[best_jank]['performance']['rendering']['jank_percentage']}%)")
            # FPS
            best_fps = max(apps, key=lambda a: data[a]["performance"]["rendering"]["approx_fps"])
            print(f"  🎯 Highest Frame Rate    : {best_fps} ({data[best_fps]['performance']['rendering']['approx_fps']} FPS)")
            # Network
            best_net = min(apps, key=lambda a: data[a]["performance"]["network"].get("download_kb", 0.0))
            print(f"  🌐 Network Data Winner   : {best_net} ({data[best_net]['performance']['network'].get('download_kb', 0.0)} KB down)")
            print("─"*55)

        print(f"\n[+] Open the visual report in your browser: file://{os.path.abspath('performance_benchmark_report.html')}\n")


def main():
    parser = argparse.ArgumentParser(description="Mobile App Performance Benchmarking Runner")
    parser.add_argument("--config", default="benchmark_config.json", help="Path to JSON config file")
    parser.add_argument("--device", help="Specific device UDID (overrides config)")
    parser.add_argument("--iterations", type=int, help="Number of startup iterations")
    parser.add_argument("--duration", type=int, help="Interactive scenario duration in seconds")
    parser.add_argument("--output", default="benchmark_results.json", help="Output JSON path")
    parser.add_argument("--html", default="performance_benchmark_report.html", help="Output HTML report path")
    args = parser.parse_args()

    config_path = args.config
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            config = json.load(f)
    else:
        print(f"[-] Config file {config_path} not found.")
        sys.exit(1)

    if args.device:
        config["device_udid"] = args.device
    if args.iterations:
        config["iterations"] = args.iterations
    if args.duration:
        config["scenario_duration_sec"] = args.duration

    orchestrator = BenchmarkOrchestrator(config)
    orchestrator.execute(output_json=args.output, output_html=args.html)


if __name__ == "__main__":
    main()
