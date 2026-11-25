"""
Telemetry Data Models for Mobile Performance Benchmarking.
Represents individual phase metrics, startup metrics, and aggregated run reports.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional


@dataclass
class PhaseMetrics:
    phase_name: str
    duration_sec: float = 0.0
    total_frames: int = 0
    janky_frames: int = 0
    jank_percentage: float = 0.0
    approx_fps: float = 60.0
    p50_frame_time_ms: float = 16.0
    p90_frame_time_ms: float = 16.0
    p95_frame_time_ms: float = 16.0
    p99_frame_time_ms: float = 16.0
    avg_cpu_percent: float = 0.0
    max_cpu_percent: float = 0.0
    p95_cpu_percent: float = 0.0
    avg_pss_mb: float = 0.0
    max_pss_mb: float = 0.0
    native_heap_mb: float = 0.0
    dalvik_heap_mb: float = 0.0
    graphics_mb: float = 0.0
    disk_read_kb: float = 0.0
    disk_write_kb: float = 0.0
    net_rx_kb: float = 0.0
    net_tx_kb: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StartupMetrics:
    cold_start_to_mpin_ms: Optional[int] = None
    hot_resume_ms: Optional[int] = None
    mpin_to_dashboard_ms: Optional[int] = None
    cold_start_runs_ms: List[int] = field(default_factory=list)
    hot_resume_runs_ms: List[int] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AppBenchmarkReport:
    app_label: str
    package_name: str
    startup: StartupMetrics = field(default_factory=StartupMetrics)
    phases: Dict[str, PhaseMetrics] = field(default_factory=dict)
    ai_root_cause_analysis: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "app_label": self.app_label,
            "package_name": self.package_name,
            "startup": self.startup.to_dict(),
            "phases": {name: p.to_dict() for name, p in self.phases.items()},
            "ai_root_cause_analysis": self.ai_root_cause_analysis
        }
