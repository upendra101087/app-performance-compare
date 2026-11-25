# Mobile Perf AI: Phase-Segmented Benchmarking Framework

An AI-powered, phase-segmented mobile performance benchmarking suite for Android applications (FinTech focus: AngelOne, Groww, Dhan).

## Key Features

1. **Phase-Segmented Window Telemetry**:
   - Rather than blending the entire session into a single noisy number, the tool wraps telemetry strictly around active interaction windows using `dumpsys gfxinfo <package> reset`.
   - Records isolated **Jank %**, **FPS**, **CPU %**, and **PSS RAM** for each screen journey:
     - Cold Start to MPIN
     - MPIN Unlock
     - Hot Resume
     - Homepage 10x Scroll
     - Watchlist 10x Scroll
     - Portfolio 10x Scroll
     - Positions 10x Scroll
     - Candlestick Chart Pinch-Zoom

2. **Page Object Model (POM)**:
   - Base contract `BaseTradingPage` enforced across `GrowwPage`, `AngelOnePage`, and `DhanPage`.
   - Supports both Appium Automation and calibrated ADB Gesture fallbacks.

3. **AI Layer**:
   - **Self-Healing Agent (`ai.self_healing_agent`)**: Detects unexpected popups (rate us, promo modals, terms) via Vision/DOM inspection and dismisses them automatically.
   - **Performance Analyst (`ai.performance_analyst`)**: Runs automated Root Cause Analysis (RCA) on comparative metrics using Gemini / LLM models or the built-in diagnostic engine.

4. **Executive Visual Dashboard**:
   - Compiles interactive category winners, phase comparison matrix, and AI diagnoses into `performance_benchmark_report.html`.

## Project Structure

```
mobile-perf-ai/
├── config/
│   └── benchmark_config.json      # App packages, MPIN, devices, gesture settings
├── telemetry/
│   ├── android_collector.py       # Dumpsys gfxinfo/meminfo/am start collector
│   └── models.py                  # Dataclasses for PhaseMetrics and StartupMetrics
├── core/
│   ├── driver_factory.py          # Appium UiAutomator2 remote session factory
│   ├── gesture_engine.py          # Calibrated 10x scroll & W3C chart pinch-zoom
│   └── phase_tracker.py           # Context manager wrapping phase measurement
├── pages/
│   ├── base_trading_page.py       # Base contract for all trading apps
│   ├── groww_page.py              # Groww-specific locators & flows
│   ├── angelone_page.py           # AngelOne-specific locators & flows
│   └── dhan_page.py               # Dhan-specific locators & flows
├── ai/
│   ├── self_healing_agent.py      # Vision/DOM modal dismisser
│   ├── performance_analyst.py     # AI Root Cause Analysis (RCA)
│   └── prompt_templates.py        # LLM system prompts
├── reporting/
│   └── html_generator.py          # Generates visual dashboard
└── main_runner.py                 # Master benchmark orchestrator
```

## Running the Benchmark

```bash
cd mobile-perf-ai

# 1. Install dependencies (optional for Appium, runs in ADB fallback mode out of the box)
pip3 install -r requirements.txt

# 2. Run benchmark with default configuration
python3 main_runner.py

# 3. Specify explicit device or custom config
python3 main_runner.py --device <UDID> --config config/benchmark_config.json
```
