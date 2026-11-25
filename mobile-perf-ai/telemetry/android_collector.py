"""
Android Performance Telemetry Collector.
Captures phase-segmented windowed telemetry via Android OS diagnostics and dumpsys.
"""

import os
import re
import subprocess
import threading
import time
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

from telemetry.models import PhaseMetrics, StartupMetrics


class AndroidTelemetryCollector:
    def __init__(self, device_udid: str, package_name: str, main_activity: Optional[str] = None):
        self.device_udid = device_udid
        self.package_name = package_name
        self.main_activity = main_activity
        
        self.pid: Optional[int] = None
        self.app_uid: Optional[int] = None
        
        # Sampling state
        self._sampling = False
        self._sample_thread: Optional[threading.Thread] = None
        self._phase_name: str = "default"
        self._phase_start_time: float = 0.0
        
        # Intermediate storage
        self.cpu_samples: List[float] = []
        self.memory_samples: List[Dict[str, float]] = []
        self.disk_start: Dict[str, int] = {}
        self.disk_end: Dict[str, int] = {}
        self.net_start: Dict[str, int] = {"rx_bytes": 0, "tx_bytes": 0}
        self.net_end: Dict[str, int] = {"rx_bytes": 0, "tx_bytes": 0}

    def run_adb(self, cmd_args: List[str], timeout_sec: int = 15) -> str:
        """Executes an adb command with target device UDID and timeout."""
        cmd = ["adb", "-s", self.device_udid] + cmd_args
        try:
            res = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout_sec
            )
            return res.stdout.strip()
        except subprocess.TimeoutExpired:
            return ""
        except Exception:
            return ""

    def get_pid(self) -> Optional[int]:
        out = self.run_adb(["shell", "pidof", self.package_name])
        if out:
            pids = out.split()
            if pids and pids[0].isdigit():
                self.pid = int(pids[0])
                return self.pid

        # Fallback to ps -A
        ps_out = self.run_adb(["shell", "ps", "-A"])
        for line in ps_out.splitlines():
            if self.package_name in line:
                parts = line.split()
                if len(parts) >= 2 and parts[1].isdigit():
                    self.pid = int(parts[1])
                    return self.pid
        return None

    def get_screen_size(self) -> Tuple[int, int]:
        out = self.run_adb(["shell", "wm", "size"])
        m = re.search(r"(\d+)x(\d+)", out)
        if m:
            return int(m.group(1)), int(m.group(2))
        return 1080, 2400

    def resolve_launcher_activity(self) -> Optional[str]:
        out = self.run_adb(["shell", "cmd", "package", "resolve-activity", "--brief", self.package_name])
        for line in out.splitlines():
            line = line.strip()
            if "/" in line and not line.startswith("priority="):
                return line
        return None

    # ==========================
    # Startup Profiling
    # ==========================
    def measure_cold_start_to_mpin(self) -> Optional[int]:
        """Kills the app, initiates cold start via am start -W, and returns TotalTime in ms."""
        self.run_adb(["shell", "am", "force-stop", self.package_name])
        time.sleep(1.0)
        self.run_adb(["logcat", "-c"])

        cmd = [
            "shell", "am", "start", "-W",
            "-a", "android.intent.action.MAIN",
            "-c", "android.intent.category.LAUNCHER",
            "-p", self.package_name
        ]
        out = self.run_adb(cmd)
        
        for line in out.splitlines():
            if line.startswith("TotalTime:"):
                try:
                    return int(line.split(":")[1].strip())
                except ValueError:
                    pass
        return None

    def measure_hot_resume(self, bg_dwell_sec: float = 2.0) -> Optional[int]:
        """Minimizes the app to background, waits, and resumes it measuring launch latency."""
        # 1. Send HOME keyevent
        self.run_adb(["shell", "input", "keyevent", "3"])
        time.sleep(bg_dwell_sec)

        # 2. Resume
        cmd = [
            "shell", "am", "start", "-W",
            "-a", "android.intent.action.MAIN",
            "-c", "android.intent.category.LAUNCHER",
            "-p", self.package_name
        ]
        out = self.run_adb(cmd)
        for line in out.splitlines():
            if line.startswith("TotalTime:"):
                try:
                    return int(line.split(":")[1].strip())
                except ValueError:
                    pass
        return None

    # ==========================
    # Segmented Window Profiling
    # ==========================
    def start_profiling_window(self, phase_name: str):
        """Resets dumpsys gfxinfo and initiates background thread sampling for CPU/Memory."""
        self._phase_name = phase_name
        self._sampling = True
        self.cpu_samples = []
        self.memory_samples = []
        self._phase_start_time = time.time()

        # Reset OS frame buffer for this window
        self.run_adb(["shell", "dumpsys", "gfxinfo", self.package_name, "reset"])

        # Baselines
        self.disk_start = self._read_disk_io()
        self.net_start = self._read_network_stats()

        # Start background sampler
        self._sample_thread = threading.Thread(target=self._sampling_loop, daemon=True)
        self._sample_thread.start()

    def stop_profiling_window(self) -> PhaseMetrics:
        """Stops background sampling, parses gfxinfo for Jank and FPS, and packages PhaseMetrics."""
        self._sampling = False
        if self._sample_thread:
            self._sample_thread.join(timeout=2.0)

        duration = round(time.time() - self._phase_start_time, 2)
        self.disk_end = self._read_disk_io()
        self.net_end = self._read_network_stats()

        # Parse gfxinfo
        gfx_out = self.run_adb(["shell", "dumpsys", "gfxinfo", self.package_name])
        frame_stats = self._parse_framestats(gfx_out)

        # CPU Stats
        avg_cpu = round(float(np.mean(self.cpu_samples)), 2) if self.cpu_samples else 0.0
        max_cpu = round(float(np.max(self.cpu_samples)), 2) if self.cpu_samples else 0.0
        p95_cpu = round(float(np.percentile(self.cpu_samples, 95)), 2) if self.cpu_samples else 0.0

        # Memory Stats
        pss_vals = [m["total_pss_mb"] for m in self.memory_samples if m.get("total_pss_mb", 0) > 0]
        avg_pss = round(float(np.mean(pss_vals)), 2) if pss_vals else 0.0
        max_pss = round(float(np.max(pss_vals)), 2) if pss_vals else 0.0

        last_mem = self.memory_samples[-1] if self.memory_samples else {}
        native_heap = last_mem.get("native_heap_mb", 0.0)
        dalvik_heap = last_mem.get("dalvik_heap_mb", 0.0)
        graphics_mb = last_mem.get("graphics_mb", 0.0)

        # Delta I/O
        disk_r = round(abs(self.disk_end.get("read_bytes", 0) - self.disk_start.get("read_bytes", 0)) / 1024.0, 2)
        disk_w = round(abs(self.disk_end.get("write_bytes", 0) - self.disk_start.get("write_bytes", 0)) / 1024.0, 2)
        net_rx = round(abs(self.net_end.get("rx_bytes", 0) - self.net_start.get("rx_bytes", 0)) / 1024.0, 2)
        net_tx = round(abs(self.net_end.get("tx_bytes", 0) - self.net_start.get("tx_bytes", 0)) / 1024.0, 2)

        return PhaseMetrics(
            phase_name=self._phase_name,
            duration_sec=duration,
            total_frames=frame_stats["total_frames"],
            janky_frames=frame_stats["janky_frames"],
            jank_percentage=frame_stats["jank_percentage"],
            approx_fps=frame_stats["approx_fps"],
            p50_frame_time_ms=frame_stats["p50_frame_time_ms"],
            p90_frame_time_ms=frame_stats["p90_frame_time_ms"],
            p95_frame_time_ms=frame_stats["p95_frame_time_ms"],
            p99_frame_time_ms=frame_stats["p99_frame_time_ms"],
            avg_cpu_percent=avg_cpu,
            max_cpu_percent=max_cpu,
            p95_cpu_percent=p95_cpu,
            avg_pss_mb=avg_pss,
            max_pss_mb=max_pss,
            native_heap_mb=native_heap,
            dalvik_heap_mb=dalvik_heap,
            graphics_mb=graphics_mb,
            disk_read_kb=disk_r,
            disk_write_kb=disk_w,
            net_rx_kb=net_rx,
            net_tx_kb=net_tx
        )

    # ==========================
    # Sampling Internals
    # ==========================
    def _sampling_loop(self, interval_sec: float = 0.5):
        while self._sampling:
            pid = self.get_pid()
            if pid:
                # 1. CPU sample
                top_out = self.run_adb(["shell", "top", "-b", "-n", "1", "-p", str(pid)])
                for line in top_out.splitlines():
                    if str(pid) in line:
                        parts = line.split()
                        for p in parts:
                            if "%" in p:
                                try:
                                    self.cpu_samples.append(float(p.replace("%", "")))
                                    break
                                except ValueError:
                                    pass
                            elif re.match(r"^\d+\.\d+$", p):
                                self.cpu_samples.append(float(p))
                                break

                # 2. Memory sample
                mem_out = self.run_adb(["shell", "dumpsys", "meminfo", self.package_name])
                mem_dict = {"total_pss_mb": 0.0, "native_heap_mb": 0.0, "dalvik_heap_mb": 0.0, "graphics_mb": 0.0}
                for line in mem_out.splitlines():
                    if "TOTAL PSS:" in line:
                        parts = line.split()
                        try:
                            mem_dict["total_pss_mb"] = round(int(parts[2]) / 1024.0, 2)
                        except (IndexError, ValueError):
                            pass
                    elif "Native Heap" in line and mem_dict["native_heap_mb"] == 0:
                        parts = line.split()
                        try:
                            mem_dict["native_heap_mb"] = round(int(parts[2]) / 1024.0, 2)
                        except (IndexError, ValueError):
                            pass
                    elif "Dalvik Heap" in line and mem_dict["dalvik_heap_mb"] == 0:
                        parts = line.split()
                        try:
                            mem_dict["dalvik_heap_mb"] = round(int(parts[2]) / 1024.0, 2)
                        except (IndexError, ValueError):
                            pass
                    elif "Graphics" in line and mem_dict["graphics_mb"] == 0:
                        parts = line.split()
                        try:
                            mem_dict["graphics_mb"] = round(int(parts[1]) / 1024.0, 2)
                        except (IndexError, ValueError):
                            pass
                if mem_dict["total_pss_mb"] > 0:
                    self.memory_samples.append(mem_dict)

            time.sleep(interval_sec)

    def _parse_framestats(self, gfx_output: str) -> Dict[str, Any]:
        """Extracts native vsync frame telemetry from dumpsys gfxinfo."""
        total_m = re.search(r"Total frames rendered:\s*(\d+)", gfx_output)
        jank_m = re.search(r"Janky frames:\s*(\d+)\s*\(([\d\.]+)%\)", gfx_output)
        p50_m = re.search(r"50th percentile:\s*(\d+)ms", gfx_output)
        p90_m = re.search(r"90th percentile:\s*(\d+)ms", gfx_output)
        p95_m = re.search(r"95th percentile:\s*(\d+)ms", gfx_output)
        p99_m = re.search(r"99th percentile:\s*(\d+)ms", gfx_output)

        if total_m and jank_m:
            total_frames = int(total_m.group(1))
            janky_frames = int(jank_m.group(1))
            jank_percentage = float(jank_m.group(2))
            p50 = float(p50_m.group(1)) if p50_m else 16.0
            p90 = float(p90_m.group(1)) if p90_m else 16.0
            p95 = float(p95_m.group(1)) if p95_m else 16.0
            p99 = float(p99_m.group(1)) if p99_m else 16.0

            render_fps = round(min(60.0, 1000.0 / p50), 1) if p50 > 0 else 60.0
            effective_fps = max(1.0, min(60.0, round(render_fps * (1.0 - (jank_percentage / 100.0) * 0.5), 1)))

            return {
                "total_frames": total_frames,
                "janky_frames": janky_frames,
                "jank_percentage": jank_percentage,
                "approx_fps": effective_fps,
                "p50_frame_time_ms": p50,
                "p90_frame_time_ms": p90,
                "p95_frame_time_ms": p95,
                "p99_frame_time_ms": p99,
            }

        return {
            "total_frames": 0,
            "janky_frames": 0,
            "jank_percentage": 0.0,
            "approx_fps": 60.0,
            "p50_frame_time_ms": 16.0,
            "p90_frame_time_ms": 16.0,
            "p95_frame_time_ms": 16.0,
            "p99_frame_time_ms": 16.0,
        }

    def _read_disk_io(self) -> Dict[str, int]:
        pid = self.get_pid()
        if pid:
            out = self.run_adb(["shell", "cat", f"/proc/{pid}/io"])
            if out and "Permission denied" not in out:
                res = {"read_bytes": 0, "write_bytes": 0}
                for line in out.splitlines():
                    if "read_bytes:" in line:
                        res["read_bytes"] = int(line.split(":")[1].strip())
                    elif "write_bytes:" in line:
                        res["write_bytes"] = int(line.split(":")[1].strip())
                if res["read_bytes"] > 0 or res["write_bytes"] > 0:
                    return res
        return {"read_bytes": 0, "write_bytes": 0}

    def _read_network_stats(self) -> Dict[str, int]:
        out = self.run_adb(["shell", "cat", "/proc/net/dev"])
        if out and "Permission denied" not in out:
            rx_tot = 0
            tx_tot = 0
            for line in out.splitlines():
                if any(iface in line for iface in ["wlan", "rmnet", "ccmni", "eth"]):
                    parts = line.replace(":", " ").split()
                    if len(parts) >= 10:
                        try:
                            rx_tot += int(parts[1])
                            tx_tot += int(parts[9])
                        except (ValueError, IndexError):
                            pass
            return {"rx_bytes": rx_tot, "tx_bytes": tx_tot}
        return {"rx_bytes": 0, "tx_bytes": 0}
