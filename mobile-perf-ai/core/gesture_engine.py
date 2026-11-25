"""
Gesture Engine for Standardized Benchmark Interactions.
Implements calibrated 10x vertical scrolling, natural human pauses,
and W3C multi-touch pinch-in / pinch-out for TradingView / ChartIQ candlestick charts.
"""

import time
import subprocess
from typing import Optional, Tuple


class GestureEngine:
    def __init__(self, driver=None, device_udid: str = "auto", screen_size: Tuple[int, int] = (1080, 2400)):
        self.driver = driver
        self.device_udid = device_udid
        self.screen_width, self.screen_height = screen_size

    def _run_adb_input(self, cmd_args):
        cmd = ["adb"]
        if self.device_udid and self.device_udid != "auto":
            cmd += ["-s", self.device_udid]
        cmd += ["shell", "input"] + cmd_args
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def scroll_vertical_n_times(self, times: int = 10, direction: str = "down", duration_ms: int = 350, pause_sec: float = 0.4):
        """
        Executes N continuous vertical scrolls with natural velocity.
        """
        center_x = self.screen_width // 2
        if direction == "down":
            start_y = int(self.screen_height * 0.75)
            end_y = int(self.screen_height * 0.25)
        else:
            start_y = int(self.screen_height * 0.25)
            end_y = int(self.screen_height * 0.75)

        for _ in range(times):
            if self.driver:
                try:
                    self.driver.swipe(center_x, start_y, center_x, end_y, duration_ms)
                except Exception:
                    self._run_adb_input(["swipe", str(center_x), str(start_y), str(center_x), str(end_y), str(duration_ms)])
            else:
                self._run_adb_input(["swipe", str(center_x), str(start_y), str(center_x), str(end_y), str(duration_ms)])
            
            time.sleep(pause_sec)

    def pinch_zoom(self, cycles: int = 5, pause_sec: float = 0.5):
        """
        Executes two-finger pinch-out (zoom in) and pinch-in (zoom out) on charts.
        Uses Appium's W3C Actions or multi-pointer gesture.
        """
        if self.driver and hasattr(self.driver, "pinch_open"):
            for _ in range(cycles):
                try:
                    # Zoom In
                    self.driver.pinch_open(percent=75, steps=30)
                    time.sleep(pause_sec)
                    # Zoom Out
                    self.driver.pinch_close(percent=75, steps=30)
                    time.sleep(pause_sec)
                except Exception as e:
                    print(f"[-] Appium pinch error: {e}")
                    break
        else:
            # Fallback horizontal swipe to interact with chart timeframes if pinch driver is unattached
            center_y = self.screen_height // 2
            for _ in range(cycles):
                # Pan right
                self._run_adb_input(["swipe", str(int(self.screen_width * 0.8)), str(center_y), str(int(self.screen_width * 0.2)), str(center_y), "300"])
                time.sleep(pause_sec)
                # Pan left
                self._run_adb_input(["swipe", str(int(self.screen_width * 0.2)), str(center_y), str(int(self.screen_width * 0.8)), str(center_y), "300"])
                time.sleep(pause_sec)

    def tap_coordinates(self, x: int, y: int):
        if self.driver:
            try:
                from selenium.webdriver.common.actions.action_builder import ActionBuilder
                from selenium.webdriver.common.actions.pointer_input import PointerInput
                from selenium.webdriver.common.actions import interaction

                actions = ActionBuilder(self.driver, mouse=PointerInput(interaction.POINTER_TOUCH, "touch"))
                actions.pointer_action.move_to_location(x, y)
                actions.pointer_action.pointer_down()
                actions.pointer_action.pause(0.1)
                actions.pointer_action.pointer_up()
                actions.perform()
                return
            except Exception:
                pass
        self._run_adb_input(["tap", str(x), str(y)])
