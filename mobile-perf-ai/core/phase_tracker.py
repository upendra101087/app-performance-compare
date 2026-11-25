"""
Phase Tracker Context Manager.
Coordinates between UI Automation (Appium/Gestures) and the Android Telemetry Collector.
Ensures that dumpsys gfxinfo, CPU, and RAM are measured strictly during the active gesture window.
"""

import time
from typing import Callable, Any
from telemetry.android_collector import AndroidTelemetryCollector
from telemetry.models import PhaseMetrics


class PhaseTracker:
    def __init__(self, collector: AndroidTelemetryCollector):
        self.collector = collector

    def profile_phase(self, phase_name: str, action_func: Callable[[], Any], settle_delay_sec: float = 0.8) -> PhaseMetrics:
        """
        1. Waits for initial screen animations to settle.
        2. Resets the OS frame buffer and begins continuous CPU/RAM sampling.
        3. Executes the action (e.g. 10 scrolls, chart pinch).
        4. Stops sampling and returns isolated PhaseMetrics for this screen.
        """
        print(f"\n[*] ─── Profiling Phase: {phase_name} ───")
        if settle_delay_sec > 0:
            time.sleep(settle_delay_sec)

        # 1. Start profiling window
        self.collector.start_profiling_window(phase_name)

        # 2. Execute UI Action
        t_start = time.time()
        try:
            action_func()
        except Exception as e:
            print(f"[-] Warning: Action in phase '{phase_name}' raised error: {e}")
        elapsed = round(time.time() - t_start, 2)

        # 3. Stop profiling window
        metrics = self.collector.stop_profiling_window()
        metrics.duration_sec = elapsed

        print(f"[✓] {phase_name:<25} | Duration: {elapsed}s | Jank: {metrics.jank_percentage}% | FPS: {metrics.approx_fps} | PSS: {metrics.avg_pss_mb} MB")
        return metrics
