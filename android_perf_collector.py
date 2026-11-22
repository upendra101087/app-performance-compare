#!/usr/bin/env python3
"""
Android Performance Telemetry Collector (Non-invasive / Black-box compatible)
Supports both internal apps and competitor production builds without source code.
Captures:
- Cold & Hot Startup Time (ms)
- CPU Usage (%)
- Memory (Total PSS, Native, Dalvik, Graphics in MB)
- Jank & FPS (via dumpsys gfxinfo)
- Disk I/O (File-backed cache & SQLite dirty pages in KB)
- Real-time Network Data (Rx Download & Tx Upload bytes via /proc/net/dev and netstats)
"""

import subprocess
import time
import threading
import re
import numpy as np
from typing import Dict, Any, List, Optional, Tuple


class AndroidPerfCollector:
    def __init__(self, device_udid: str, package_name: str, main_activity: Optional[str] = None):
        self.device_udid = device_udid
        self.package_name = package_name
        self.main_activity = main_activity
        self.pid: Optional[int] = None
        self.app_uid: Optional[int] = None
        self._sampling = False
        self._sample_thread: Optional[threading.Thread] = None
        self.last_launch_error: str = ""
        
        # Metric stores
        self.cpu_samples: List[float] = []
        self.memory_samples: List[Dict[str, float]] = []  # Total PSS, Native, Dalvik, Graphics
        self.disk_start: Dict[str, int] = {}
        self.disk_end: Dict[str, int] = {}
        self.net_start: Dict[str, int] = {"rx_bytes": 0, "tx_bytes": 0}
        self.net_end: Dict[str, int] = {"rx_bytes": 0, "tx_bytes": 0}

    def _run_adb(self, cmd_args: List[str]) -> str:
        cmd = ["adb", "-s", self.device_udid] + cmd_args
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            out = res.stdout.strip()
            err = res.stderr.strip()
            if res.returncode != 0 and err:
                self.last_launch_error = err
                return out if out else err
            return out
        except Exception as e:
            self.last_launch_error = str(e)
            return ""

    def is_app_installed(self) -> bool:
        """Verifies if the target package is installed on the device."""
        out = self._run_adb(["shell", "pm", "path", self.package_name])
        return "package:" in out

    def get_screen_size(self) -> Tuple[int, int]:
        """Queries physical screen resolution for responsive swipe coordinates."""
        out = self._run_adb(["shell", "wm", "size"])
        m = re.search(r"(\d+)x(\d+)", out)
        if m:
            return int(m.group(1)), int(m.group(2))
        return 1080, 2400

    def resolve_launcher_activity(self) -> Optional[str]:
        """Dynamically queries package manager for the default exported launcher activity."""
        out = self._run_adb(["shell", "cmd", "package", "resolve-activity", "--brief", self.package_name])
        lines = [line.strip() for line in out.splitlines() if line.strip()]
        for line in lines:
            if "/" in line and not line.startswith("priority="):
                return line
        return None

    def get_pid(self) -> Optional[int]:
        # Method 1: pidof
        out = self._run_adb(["shell", "pidof", self.package_name])
        if out:
            pids = out.split()
            if pids and pids[0].isdigit():
                self.pid = int(pids[0])
                return self.pid

        # Method 2: ps -A fallback (handles sub-processes or OEM ROMs)
        ps_out = self._run_adb(["shell", "ps", "-A"])
        for line in ps_out.splitlines():
            if self.package_name in line:
                parts = line.split()
                if len(parts) >= 2 and parts[1].isdigit():
                    self.pid = int(parts[1])
                    return self.pid
        return None

    def get_uid(self) -> Optional[int]:
        if self.app_uid:
            return self.app_uid

        # Method 1: dumpsys package (most reliable on all Android versions)
        out = self._run_adb(["shell", "dumpsys", "package", self.package_name])
        match = re.search(r"userId=(\d+)", out)
        if match:
            self.app_uid = int(match.group(1))
            return self.app_uid

        # Method 2: pm list packages -U
        out2 = self._run_adb(["shell", "pm", "list", "packages", "-U", self.package_name])
        match2 = re.search(r"uid:(\d+)", out2)
        if match2:
            self.app_uid = int(match2.group(1))
            return self.app_uid

        return None

    # ==========================
    # 1. Startup Time Measurement
    # ==========================
    def _execute_launch(self) -> str:
        # Strategy 1: Universal Launcher Intent (works for all apps without non-exported security exceptions)
        out = self._run_adb([
            "shell", "am", "start", "-W",
            "-a", "android.intent.action.MAIN",
            "-c", "android.intent.category.LAUNCHER",
            "-p", self.package_name
        ])
        if "TotalTime:" in out:
            return out

        # Strategy 2: Explicit component if specified
        if self.main_activity:
            target = f"{self.package_name}/{self.main_activity}" if "/" not in self.main_activity else self.main_activity
            alt_out = self._run_adb(["shell", "am", "start", "-W", "-n", target])
            if "TotalTime:" in alt_out:
                return alt_out
            if "SecurityException" in alt_out or "Error" in alt_out:
                self.last_launch_error = alt_out

        # Strategy 3: Dynamically resolved launcher activity
        resolved = self.resolve_launcher_activity()
        if resolved:
            alt_out2 = self._run_adb(["shell", "am", "start", "-W", "-n", resolved])
            if "TotalTime:" in alt_out2:
                return alt_out2

        # Strategy 4: Fallback to monkey
        t0 = time.time()
        self._run_adb(["shell", "monkey", "-p", self.package_name, "-c", "android.intent.category.LAUNCHER", "1"])
        for _ in range(25):
            if self.get_pid():
                elapsed = int((time.time() - t0) * 1000)
                return f"TotalTime: {elapsed}\nWaitTime: {elapsed}"
            time.sleep(0.1)

        return out

    def measure_cold_startup(self) -> Dict[str, Any]:
        self._run_adb(["shell", "am", "force-stop", self.package_name])
        time.sleep(1.0)
        self._run_adb(["logcat", "-c"])

        out = self._execute_launch()

        result = {"cold_this_time_ms": None, "cold_total_time_ms": None, "cold_wait_time_ms": None}
        for line in out.splitlines():
            if line.startswith("ThisTime:"):
                result["cold_this_time_ms"] = int(line.split(":")[1].strip())
            elif line.startswith("TotalTime:"):
                result["cold_total_time_ms"] = int(line.split(":")[1].strip())
            elif line.startswith("WaitTime:"):
                result["cold_wait_time_ms"] = int(line.split(":")[1].strip())

        if result["cold_total_time_ms"] is None and self.last_launch_error:
            result["error"] = self.last_launch_error

        return result

    def measure_hot_startup(self) -> Dict[str, Any]:
        self._run_adb(["shell", "input", "keyevent", "3"])
        time.sleep(2.0)

        out = self._execute_launch()

        result = {"hot_total_time_ms": None, "hot_wait_time_ms": None}
        for line in out.splitlines():
            if line.startswith("TotalTime:"):
                result["hot_total_time_ms"] = int(line.split(":")[1].strip())
            elif line.startswith("WaitTime:"):
                result["hot_wait_time_ms"] = int(line.split(":")[1].strip())

        return result

    # ==========================
    # 2. Disk & Network Baselines
    # ==========================
    def _read_disk_io(self) -> Dict[str, int]:
        """
        Attempts to read /proc/<pid>/io if root is available.
        On non-root consumer devices (where /proc/<pid>/io is SELinux-restricted),
        measures file-backed cache pages and SQLite dirty database buffers from dumpsys meminfo.
        """
        pid = self.get_pid()
        if pid:
            out = self._run_adb(["shell", "cat", f"/proc/{pid}/io"])
            if out and "Permission denied" not in out:
                res = {"read_bytes": 0, "write_bytes": 0}
                for line in out.splitlines():
                    if "read_bytes:" in line:
                        res["read_bytes"] = int(line.split(":")[1].strip())
                    elif "write_bytes:" in line:
                        res["write_bytes"] = int(line.split(":")[1].strip())
                if res["read_bytes"] > 0 or res["write_bytes"] > 0:
                    return res

        # Non-root fallback: Inspect File Mappings (Disk Read) & SQLite/Private Dirty (Disk Write) via meminfo
        mem_out = self._run_adb(["shell", "dumpsys", "meminfo", self.package_name])
        read_kb = 0
        write_kb = 0
        for line in mem_out.splitlines():
            # File-backed mmap (read from disk flash storage)
            if ".so mmap" in line or "jar mmap" in line or "apk mmap" in line:
                parts = line.split()
                if len(parts) >= 2 and parts[1].isdigit():
                    read_kb += int(parts[1])
            # SQLite cache & database writes
            elif "SQLite:" in line or "DATABASES" in line or "Private Dirty:" in line:
                nums = re.findall(r"\b(\d+)\b", line)
                if nums:
                    write_kb += int(nums[0])

        return {"read_bytes": read_kb * 1024, "write_bytes": write_kb * 1024}

    def _read_network_stats(self) -> Dict[str, int]:
        """
        Queries network bytes using a multi-tier strategy:
        1. Real-time live interface stats (/proc/net/dev) - Accessible on ALL non-root Android devices!
        2. Kernel /proc/uid_stat/<uid>/ (if readable)
        3. dumpsys netstats detail
        """
        # --- Strategy 1: Real-time Live Interface Traffic (/proc/net/dev) ---
        # World-readable (0444) on all Android versions. Gives instantaneous byte accuracy.
        dev_out = self._run_adb(["shell", "cat", "/proc/net/dev"])
        if dev_out and "Permission denied" not in dev_out:
            rx_total = 0
            tx_total = 0
            for line in dev_out.splitlines():
                # Focus on active network interfaces (Wi-Fi, LTE, 5G)
                if any(iface in line for iface in ["wlan", "rmnet", "ccmni", "eth", "pdp"]):
                    parts = line.replace(":", " ").split()
                    if len(parts) >= 10:
                        try:
                            rx_total += int(parts[1])  # rx_bytes
                            tx_total += int(parts[9])  # tx_bytes
                        except (ValueError, IndexError):
                            pass
            if rx_total > 0 or tx_total > 0:
                return {"rx_bytes": rx_total, "tx_bytes": tx_total}

        # --- Strategy 2: Kernel uid_stat ---
        uid = self.get_uid()
        if uid:
            rcv = self._run_adb(["shell", "cat", f"/proc/uid_stat/{uid}/tcp_rcv"])
            snd = self._run_adb(["shell", "cat", f"/proc/uid_stat/{uid}/tcp_snd"])
            if rcv.isdigit() and snd.isdigit():
                return {"rx_bytes": int(rcv), "tx_bytes": int(snd)}

        # --- Strategy 3: dumpsys netstats ---
        if uid:
            ns_out = self._run_adb(["shell", "dumpsys", "netstats", "--uid", str(uid)])
            if not ns_out or f"uid={uid}" not in ns_out:
                ns_out = self._run_adb(["shell", "dumpsys", "netstats"])

            rx_total = 0
            tx_total = 0
            lines = ns_out.splitlines()
            in_uid_section = False
            for line in lines:
                if f"uid={uid}" in line:
                    in_uid_section = True
                elif "uid=" in line and f"uid={uid}" not in line:
                    in_uid_section = False

                if in_uid_section or f"uid={uid}" in line:
                    for r in re.findall(r"rxBytes=(\d+)", line):
                        rx_total += int(r)
                    for t in re.findall(r"txBytes=(\d+)", line):
                        tx_total += int(t)
                    for r in re.findall(r"\brb=(\d+)", line):
                        rx_total += int(r)
                    for t in re.findall(r"\btb=(\d+)", line):
                        tx_total += int(t)

            return {"rx_bytes": rx_total, "tx_bytes": tx_total}

        return {"rx_bytes": 0, "tx_bytes": 0}

    # ==========================
    # 3. Continuous Sampling (CPU, RAM)
    # ==========================
    def _sample_loop(self, interval_sec: float = 0.5):
        while self._sampling:
            pid = self.get_pid()
            if pid:
                # 1. CPU Sample via top
                top_out = self._run_adb(["shell", "top", "-b", "-n", "1", "-p", str(pid)])
                for line in top_out.splitlines():
                    if str(pid) in line:
                        parts = line.split()
                        for part in parts:
                            if "%" in part:
                                try:
                                    self.cpu_samples.append(float(part.replace("%", "")))
                                    break
                                except ValueError:
                                    pass
                            elif re.match(r"^\d+\.\d+$", part):
                                self.cpu_samples.append(float(part))
                                break

                # 2. Memory Sample via dumpsys meminfo
                mem_out = self._run_adb(["shell", "dumpsys", "meminfo", self.package_name])
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

    def start_profiling(self):
        """Resets gfxinfo and begins periodic background sampling for CPU, Memory, Disk, and Network."""
        self._sampling = True
        self.cpu_samples = []
        self.memory_samples = []
        
        # Reset frame rendering stats
        self._run_adb(["shell", "dumpsys", "gfxinfo", self.package_name, "reset"])
        
        # Record baselines
        self.disk_start = self._read_disk_io()
        self.net_start = self._read_network_stats()

        # Start sampling thread
        self._sample_thread = threading.Thread(target=self._sample_loop, daemon=True)
        self._sample_thread.start()

    def stop_profiling(self) -> Dict[str, Any]:
        """Stops profiling, pulls framestats, and computes aggregated metrics."""
        self._sampling = False
        if self._sample_thread:
            self._sample_thread.join(timeout=2.0)

        # Baseline end values
        self.disk_end = self._read_disk_io()
        self.net_end = self._read_network_stats()

        # Parse gfxinfo for Jank and FPS
        gfx_out = self._run_adb(["shell", "dumpsys", "gfxinfo", self.package_name])
        frame_metrics = self._parse_framestats(gfx_out)

        # Compute summary statistics
        avg_cpu = round(float(np.mean(self.cpu_samples)), 2) if self.cpu_samples else 0.0
        max_cpu = round(float(np.max(self.cpu_samples)), 2) if self.cpu_samples else 0.0
        p95_cpu = round(float(np.percentile(self.cpu_samples, 95)), 2) if self.cpu_samples else 0.0

        pss_values = [m["total_pss_mb"] for m in self.memory_samples if m["total_pss_mb"] > 0]
        avg_pss = round(float(np.mean(pss_values)), 2) if pss_values else 0.0
        max_pss = round(float(np.max(pss_values)), 2) if pss_values else 0.0

        disk_read_kb = round(abs(self.disk_end.get("read_bytes", 0) - self.disk_start.get("read_bytes", 0)) / 1024.0, 2)
        disk_write_kb = round(abs(self.disk_end.get("write_bytes", 0) - self.disk_start.get("write_bytes", 0)) / 1024.0, 2)

        net_rx_kb = round(abs(self.net_end.get("rx_bytes", 0) - self.net_start.get("rx_bytes", 0)) / 1024.0, 2)
        net_tx_kb = round(abs(self.net_end.get("tx_bytes", 0) - self.net_start.get("tx_bytes", 0)) / 1024.0, 2)

        return {
            "cpu": {
                "avg_percent": avg_cpu,
                "max_percent": max_cpu,
                "p95_percent": p95_cpu,
                "samples_count": len(self.cpu_samples),
            },
            "memory": {
                "avg_pss_mb": avg_pss,
                "max_pss_mb": max_pss,
                "last_sample": self.memory_samples[-1] if self.memory_samples else {},
            },
            "rendering": frame_metrics,
            "disk": {
                "read_kb": disk_read_kb,
                "write_kb": disk_write_kb,
            },
            "network": {
                "download_kb": net_rx_kb,
                "upload_kb": net_tx_kb,
            }
        }

    # ==========================
    # 4. Framestats Parser (Jank & FPS)
    # ==========================
    def _parse_framestats(self, gfx_output: str) -> Dict[str, Any]:
        """
        Parses dumpsys gfxinfo output.
        Strategy 1: Native Android OS summary table (Total frames rendered, Janky frames, percentiles)
        Strategy 2: Parse ---PROFILEDATA--- with dynamically resolved column indexes and bounds checking
        """
        # --- Strategy 1: Native OS-level aggregate summary table ---
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

            if p50 > 0:
                render_fps = round(min(60.0, 1000.0 / p50), 1)
            else:
                render_fps = 60.0

            effective_fps = round(render_fps * (1.0 - (jank_percentage / 100.0) * 0.5), 1)
            effective_fps = max(1.0, min(60.0, effective_fps))

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

        # --- Strategy 2: Detailed PROFILEDATA parse ---
        lines = gfx_output.splitlines()
        in_framestats = False
        headers = []
        iv_idx = -1
        fc_idx = -1
        frame_durations_ms: List[float] = []
        janky_frames = 0

        for line in lines:
            if "---PROFILEDATA---" in line:
                in_framestats = True
                continue
            if not in_framestats:
                continue
            if in_framestats and line.startswith("Flags,"):
                headers = [h.strip() for h in line.split(",")]
                if "IntendedVsync" in headers and "FrameCompleted" in headers:
                    iv_idx = headers.index("IntendedVsync")
                    fc_idx = headers.index("FrameCompleted")
                continue
            if in_framestats and line.startswith("---PROFILEDATA---"):
                break

            parts = [p.strip() for p in line.split(",") if p.strip()]
            if iv_idx >= 0 and fc_idx >= 0 and len(parts) > max(iv_idx, fc_idx):
                try:
                    iv = int(parts[iv_idx])
                    fc = int(parts[fc_idx])
                    if iv > 0 and fc > iv:
                        duration_ms = (fc - iv) / 1_000_000.0
                        if 1.0 <= duration_ms <= 500.0:
                            frame_durations_ms.append(duration_ms)
                            if duration_ms > 16.67:
                                janky_frames += 1
                except (ValueError, IndexError):
                    continue

        total_frames = len(frame_durations_ms)
        if total_frames == 0:
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

        mean_duration = float(np.mean(frame_durations_ms))
        fps = round(min(60.0, 1000.0 / mean_duration), 1) if mean_duration > 0 else 60.0
        jank_pct = round((janky_frames / total_frames) * 100.0, 2)

        return {
            "total_frames": total_frames,
            "janky_frames": janky_frames,
            "jank_percentage": jank_pct,
            "approx_fps": fps,
            "p50_frame_time_ms": round(float(np.percentile(frame_durations_ms, 50)), 2),
            "p90_frame_time_ms": round(float(np.percentile(frame_durations_ms, 90)), 2),
            "p95_frame_time_ms": round(float(np.percentile(frame_durations_ms, 95)), 2),
            "p99_frame_time_ms": round(float(np.percentile(frame_durations_ms, 99)), 2),
        }
