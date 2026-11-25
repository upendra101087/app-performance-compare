"""
Abstract Base Contract for Trading App Page Objects.
Guarantees that all target apps (Groww, AngelOne, Dhan, etc.) execute the identical semantic user journey.
"""

from abc import ABC, abstractmethod
import time
from typing import Optional
from core.gesture_engine import GestureEngine


class BaseTradingPage(ABC):
    def __init__(self, driver=None, gesture_engine: Optional[GestureEngine] = None, ai_agent=None):
        self.driver = driver
        self.gestures = gesture_engine or GestureEngine(driver=driver)
        self.ai_agent = ai_agent

    @property
    @abstractmethod
    def app_label(self) -> str:
        """Human-readable app label, e.g. 'Groww' or 'AngelOne'."""
        pass

    @property
    @abstractmethod
    def package_name(self) -> str:
        """Target Android package name."""
        pass

    @abstractmethod
    def enter_mpin(self, pin: str) -> bool:
        """Enters the 4-digit or 6-digit MPIN on the custom or system keypad."""
        pass

    def scroll_homepage(self, times: int = 10):
        """Scrolls down the main dashboard/home feed N times."""
        self.gestures.scroll_vertical_n_times(times=times)

    @abstractmethod
    def navigate_to_watchlist(self) -> bool:
        """Navigates from current screen to the primary Watchlist."""
        pass

    def scroll_watchlist(self, times: int = 10):
        """Scrolls through stocks/indices in the Watchlist N times."""
        self.gestures.scroll_vertical_n_times(times=times)

    @abstractmethod
    def navigate_to_portfolio(self) -> bool:
        """Navigates to the Portfolio/Holdings screen."""
        pass

    def scroll_portfolio(self, times: int = 10):
        """Scrolls through holdings N times."""
        self.gestures.scroll_vertical_n_times(times=times)

    @abstractmethod
    def navigate_to_positions(self) -> bool:
        """Navigates to the Orders/Positions screen."""
        pass

    def scroll_positions(self, times: int = 10):
        """Scrolls through open/closed positions N times."""
        self.gestures.scroll_vertical_n_times(times=times)

    @abstractmethod
    def open_chart(self) -> bool:
        """Opens the candlestick/TradingView chart for the first visible stock."""
        pass

    def pinch_zoom_chart(self, cycles: int = 5):
        """Executes two-finger pinch-in / pinch-out zoom on the chart canvas."""
        self.gestures.pinch_zoom(cycles=cycles)

    # Helper for safe element clicks with AI fallback
    def _click_or_ai_fallback(self, by, locator: str, description: str, timeout_sec: float = 5.0) -> bool:
        if self.driver:
            try:
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                elem = WebDriverWait(self.driver, timeout_sec).until(
                    EC.element_to_be_clickable((by, locator))
                )
                elem.click()
                return True
            except Exception as e:
                print(f"[-] Could not find '{description}' using {locator}: {e}")
                if self.ai_agent:
                    print(f"[*] Calling AI Agent to locate '{description}' via Vision/DOM...")
                    return self.ai_agent.resolve_and_click(self.driver, description)
        return False
