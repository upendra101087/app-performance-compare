# In-House Mobile Device Farm & Non-Invasive Performance Benchmarking Suite

A production-ready solution for managing an in-house mobile device farm (Android & iOS) paired with an automated, non-invasive performance benchmarking suite. Measure and compare critical performance telemetry—such as **Cold/Hot Startup Latencies**, **Memory (PSS)**, **CPU Utilization**, **Jank Percentage**, **FPS**, **Live Network Upload/Download**, and **Disk I/O**—across production applications and competitors without requiring access to source code or rooted/jailbroken devices.

---

## 🌟 Key Highlights

- **In-House Device Farm Infrastructure**:
  - Central Hub configuration for a dedicated Mac Mini using Appium 2 and `appium-device-farm`.
  - Distributed Node setup allowing remote developers and QA team members to contribute physical devices from their local machines.
  - Interactive bash installers (`setup-macmini.sh`, `setup-remote-node.sh`) with intelligent skip/upgrade prompts for existing tools.
  - Integrated web dashboard for live device management, video streaming, and session tracking.

- **Non-Invasive Telemetry Collection (No Root / No SDK Required)**:
  - **Universal App Launcher**: Auto-detects launcher activities via Android package manager and triggers native `MAIN`/`LAUNCHER` intents, bypassing `SecurityException` blocks on production apps with `android:exported="false"`.
  - **Cold & Hot Start Latency**: High-precision startup measurement using `am start -W`.
  - **Jank & FPS Metrics**: Fully compatible with Android 12, 13, 14, and 15 by parsing OS aggregate summaries from `dumpsys gfxinfo`, avoiding CSV index drift.
  - **Real-Time Network Telemetry**: Reads `/proc/net/dev` delta counters per interface (`wlan0`, `rmnet`), overcoming the 60–120s eBPF kernel flush delay in `NetworkStatsService`.
  - **Disk I/O Profiling**: Tracks active memory-mapped files (`.so`, `.apk` mmap reads) and SQLite/Private Dirty page writes via `dumpsys meminfo`.
  - **Memory (PSS) & CPU %**: Accurate breakdown of system and process resources.

- **Automated Multi-App Competitor Benchmarking**:
  - Round-robin multi-iteration runner (`benchmark_orchestrator.py`) with cooldown cycles to avoid thermal throttling.
  - Real-time terminal scoreboard with clear winner identification (`🏆`).
  - Interactive HTML dashboard (`generate_comparison_report.py`) powered by Chart.js with separate comparison graphs for each performance dimension.

- **Ready-to-Run Appium Automation Client**:
  - Sample Java project (`shopeasy-appium-java`) using Appium Java Client 9.x and Selenium 4.x tailored for the local device farm.

---

## 📁 Repository Structure

```
mobile-device-farm-perf/
├── setup-macmini.sh              # Interactive Hub installer (Homebrew, Node, Appium, Android/iOS tools)
├── setup-remote-node.sh          # Interactive Remote Node contributor installer
├── hub-config.json               # Appium 2 Hub config with device-farm plugin enabled
├── node-config.json              # Appium 2 Remote Node config routing to central Hub
│
├── benchmark_config.json         # Benchmarking target configuration (apps, iterations, duration)
├── benchmark_orchestrator.py     # Multi-iteration benchmarking runner with terminal scoreboard
├── android_perf_collector.py     # Core non-invasive Android performance telemetry engine
├── ios_perf_collector.py         # iOS performance telemetry collector (tidevice / XCUITest)
├── generate_comparison_report.py # Generates interactive HTML dashboard with Chart.js
├── benchmark_results.json        # Telemetry results from physical device benchmark runs
├── performance_benchmark_report.html # Compiled interactive HTML comparison dashboard
│
└── shopeasy-appium-java/         # Complete Appium Java Client 9.x test project
    ├── pom.xml
    ├── testng.xml
    ├── README.md
    └── src/test/java/com/example/shopeasy/ShopEasyDeviceFarmTest.java
```

---

## 🚀 Quick Start Guide

### 1. Set Up the Central Hub (Mac Mini)

Run the interactive setup script on the Mac Mini. It checks for existing tools (Homebrew, Node.js, OpenJDK 17+, Android SDK, Xcode CLI, Appium 2, UiAutomator2, XCUITest, `appium-device-farm`) and prompts whether to skip or upgrade each dependency:

```bash
chmod +x setup-macmini.sh
./setup-macmini.sh
```

*Non-interactive modes:*
- `./setup-macmini.sh --yes`: Auto-upgrade all tools without prompting.
- `./setup-macmini.sh --keep`: Auto-keep existing versions without upgrading.

#### Start the Central Hub:
```bash
appium server --use-plugins=device-farm --config ./hub-config.json
```
- **Hub Endpoint**: `http://127.0.0.1:31337/wd/hub`
- **Device Farm Dashboard**: `http://localhost:31337/device-farm`

---

### 2. Set Up a Remote Node (Contributor Machine)

Team members can connect their local physical devices to the central farm:

```bash
chmod +x setup-remote-node.sh
./setup-remote-node.sh
```

#### Start the Remote Node:
```bash
appium server --use-plugins=device-farm --config ./node-config.json
```
The node automatically registers all connected Android and iOS devices with the central Hub.

---

## 📊 Performance Benchmarking Suite

### Configure Your Apps (`benchmark_config.json`)

Define target apps, number of test iterations, and interaction durations:

```json
{
  "platform": "Android",
  "device_udid": "auto",
  "iterations": 3,
  "scenario_duration_sec": 15,
  "apps": [
    {
      "label": "Angelone",
      "package_name": "com.msf.angelmobile",
      "main_activity": "com.angelbroking.spark.common.MainActivity"
    },
    {
      "label": "Groww",
      "package_name": "com.nextbillion.groww",
      "main_activity": "com.nextbillion.groww.genesys.explore.activities.MainNativeActivity"
    }
  ]
}
```

> **Note**: Even if `main_activity` is unspecified or internal (`exported="false"`), `android_perf_collector.py` auto-resolves the launcher intent from the device's package manager.

### Run the Benchmark

Make sure your target device is connected via ADB (`adb devices`), then execute:

```bash
python3 benchmark_orchestrator.py
```

### Live Terminal Scoreboard Output

At the end of the run, an aggregated scoreboard highlights the winning application across every category:

```
===================================================================================================================================
App Label        | Cold (ms) | Hot (ms) | Avg CPU  | Avg RAM    | Jank %  | FPS    | Net Down  | Net Up    | Disk Read | Disk Write
===================================================================================================================================
Angelone         | 496 ms    | 42 ms    | 7.96%    | 257.34 MB  | 22.35%  | 53.3   | 429.15 KB | 38.20 KB  | 14.20 MB  | 2.10 MB   
Groww            | 525 ms    | 49 ms    | 32.09%   | 356.37 MB  | 7.03%   | 57.9   | 512.40 KB | 45.10 KB  | 18.50 MB  | 3.40 MB   
===================================================================================================================================

🏆 CATEGORY WINNERS & PERFORMANCE HIGHLIGHTS:
  * Startup (Cold):         🏆 Angelone (496 ms vs 525 ms)
  * Startup (Hot):          🏆 Angelone (42 ms vs 49 ms)
  * CPU Efficiency:         🏆 Angelone (7.96% vs 32.09%)
  * Memory Footprint:       🏆 Angelone (257.34 MB vs 356.37 MB)
  * Frame Smoothness (FPS): 🏆 Groww (57.9 FPS vs 53.3 FPS)
  * UI Stability (Low Jank):🏆 Groww (7.03% vs 22.35%)
  * Network Data Consumed:  🏆 Angelone (429.15 KB vs 512.40 KB)
  * Disk I/O Efficiency:    🏆 Angelone (14.20 MB vs 18.50 MB)

[+] Raw telemetry data saved to: benchmark_results.json
[+] HTML Report generated at: performance_benchmark_report.html
```

---

## 📈 Interactive HTML Comparison Dashboard

Generate or regenerate the HTML dashboard at any time:

```bash
python3 generate_comparison_report.py
```

Open `performance_benchmark_report.html` in any browser to explore:
- **Winner Badges (`🏆 WINNER`)** on metric cards with percentage improvements.
- **Dedicated Chart.js Visualizations**:
  1. *Cold & Hot App Startup Time (ms)* (Lower is better)
  2. *Resource Consumption: CPU % vs. RAM PSS (MB)* (Lower is better)
  3. *Display Smoothness: FPS vs. Jank %* (Higher FPS & Lower Jank are better)
  4. *Network Bandwidth: Download vs. Upload (KB)* (Efficiency comparison)
  5. *Storage I/O: Disk Read vs. Write (MB)* (Lower is better)
- **Iteration Consistency Breakdown**: Variance and stability across individual runs.

---

## ☕ Sample Appium Java Client (`shopeasy-appium-java`)

A complete Maven-based automation test verifying end-to-end device allocation and UI interaction on the device farm.

```bash
cd shopeasy-appium-java

# Run via Maven
mvn clean test

# Or run standalone without Maven
javac -cp "..." src/test/java/com/example/shopeasy/ShopEasyDeviceFarmTest.java
java -cp "..." com.example.shopeasy.ShopEasyDeviceFarmTest
```

---

## 🔬 Telemetry Methodology

| Metric | Non-Invasive ADB Collection Technique | Why this approach? |
| :--- | :--- | :--- |
| **Cold / Hot Start** | `am start -W -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -p <package>` | Works on production release APKs with unexported internal activities without `SecurityException`. |
| **CPU Utilization** | `top -b -n 1 -p <PID>` / `/proc/stat` delta calculation | Captures realistic multi-core CPU usage under load. |
| **RAM (PSS)** | `dumpsys meminfo <package>` -> `TOTAL PSS` | Measures true physical RAM share including shared libraries, not inflated VSS/RSS. |
| **Jank % & FPS** | `dumpsys gfxinfo <package>` aggregate summary parsing | Avoids CSV column offset issues introduced in Android 12+ (`Janky frames: X (Y%)`). |
| **Network Rx / Tx** | `/proc/net/dev` live interface counter deltas | Bypasses `NetworkStatsService` eBPF cache flush delay, ensuring accurate short-burst telemetry. |
| **Disk I/O** | `dumpsys meminfo` file-backed memory pages & SQLite dirty writes | Bypasses SELinux restriction (`Permission Denied` on `/proc/<pid>/io` for non-root users). |

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
