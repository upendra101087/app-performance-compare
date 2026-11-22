#!/usr/bin/env python3
"""
iOS Performance Telemetry Collector (Non-invasive / Competitor Compatible)
Supports profiling target apps and App Store competitor builds on real iOS devices.
Integrates with:
- Appium XCUITest 'mobile: startPerfRecord' / 'mobile: stopPerfRecord'
- Open-source tidevice / py-ios-device for real-time CPU, RAM, and Core Animation FPS
"""

import subprocess
import time
import json
import threading
from typing import Dict, Any, List, Optional


class IOSPerfCollector:
    def __init__(self, device_udid: str, bundle_id: str, appium_driver=None):
        self.device_udid = device_udid
        self.bundle_id = bundle_id
        self.driver = appium_driver
        self._sampling = False
        self._tidevice_process: Optional[subprocess.Popen] = None
        self.cpu_samples: List[float] = []
        self.mem_samples: List[float] = []  # In MB
        self.fps_samples: List[float] = []

    # ==========================
    # 1. Startup Time Measurement
    # ==========================
    def measure_cold_startup(self) -> Dict[str, Any]:
        """
        Measures cold startup time using Appium driver terminate + activate.
        """
        if not self.driver:
            raise ValueError("Appium driver instance required for iOS startup measurement.")

        # Terminate app
        self.driver.execute_script("mobile: terminateApp", {"bundleId": self.bundle_id})
        time.sleep(2.0)

        start_time = time.time()
        self.driver.execute_script("mobile: activateApp", {"bundleId": self.bundle_id})
        # Wait until first interactive element appears in your test script
        elapsed_ms = round((time.time() - start_time) * 1000.0, 2)

        return {
            "cold_launch_time_ms": elapsed_ms
        }

    def measure_hot_startup(self) -> Dict[str, Any]:
        """
        Measures hot startup time by backgrounding and bringing to foreground.
        """
        if not self.driver:
            raise ValueError("Appium driver instance required for iOS startup measurement.")

        self.driver.background_app(3)
        start_time = time.time()
        self.driver.execute_script("mobile: activateApp", {"bundleId": self.bundle_id})
        elapsed_ms = round((time.time() - start_time) * 1000.0, 2)

        return {
            "hot_launch_time_ms": elapsed_ms
        }

    # ==========================
    # 2. Real-Time Telemetry via tidevice sysmontap
    # ==========================
    def start_profiling_tidevice(self):
        """
        Starts background tidevice sysmontap process to read CPU, Memory footprint, and Network.
        Command: tidevice -u <udid> sysmontap <bundle_id>
        """
        self._sampling = True
        self.cpu_samples = []
        self.mem_samples = []
        self.fps_samples = []

        try:
            self._tidevice_process = subprocess.Popen(
                ["tidevice", "-u", self.device_udid, "sysmontap", self.bundle_id],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            def read_stream():
                for line in self._tidevice_process.stdout:
                    if not self._sampling:
                        break
                    # tidevice outputs JSON or formatted stats per second
                    # e.g.: {"cpu": 15.2, "memory": 85.4, "fps": 59.8}
                    if "{" in line and "}" in line:
                        try:
                            data = json.loads(line.strip())
                            if "cpu" in data:
                                self.cpu_samples.append(float(data["cpu"]))
                            if "memory" in data:
                                self.mem_samples.append(float(data["memory"]))
                            if "fps" in data:
                                self.fps_samples.append(float(data["fps"]))
                        except json.JSONDecodeError:
                            pass

            threading.Thread(target=read_stream, daemon=True).start()
        except FileNotFoundError:
            # Fallback to Appium mobile: startPerfRecord if tidevice is not installed
            if self.driver:
                self.driver.execute_script("mobile: startPerfRecord", {
                    "timeout": 60000,
                    "profileName": "Activity Monitor"
                })

    def stop_profiling_tidevice(self) -> Dict[str, Any]:
        """Stops profiling and aggregates data."""
        self._sampling = False
        if self._tidevice_process:
            self._tidevice_process.terminate()
            self._tidevice_process.wait(timeout=2.0)
            self._tidevice_process = None
        elif self.driver:
            try:
                self.driver.execute_script("mobile: stopPerfRecord", {
                    "profileName": "Activity Monitor"
                })
            except Exception:
                pass

        avg_cpu = round(sum(self.cpu_samples) / len(self.cpu_samples), 2) if self.cpu_samples else 0.0
        max_cpu = round(max(self.cpu_samples), 2) if self.cpu_samples else 0.0
        avg_mem = round(sum(self.mem_samples) / len(self.mem_samples), 2) if self.mem_samples else 0.0
        max_mem = round(max(self.mem_samples), 2) if self.mem_samples else 0.0
        avg_fps = round(sum(self.fps_samples) / len(self.fps_samples), 1) if self.fps_samples else 60.0

        janky_frames_est = sum(1 for f in self.fps_samples if f < 55.0)
        jank_pct = round((janky_frames_est / len(self.fps_samples)) * 100.0, 2) if self.fps_samples else 0.0

        return {
            "cpu": {
                "avg_percent": avg_cpu,
                "max_percent": max_cpu,
                "samples_count": len(self.cpu_samples)
            },
            "memory": {
                "avg_resident_mb": avg_mem,
                "max_resident_mb": max_mem
            },
            "rendering": {
                "avg_fps": avg_fps,
                "jank_percentage": jank_pct,
                "samples_count": len(self.fps_samples)
            }
        }
