"""
AngelOne App Page Object (com.msf.angelmobile).
Encapsulates navigation, PIN entry, Watchlist tabs, Portfolio, Orders/Positions, and Charts.
"""

import time
from pages.base_trading_page import BaseTradingPage

try:
    from appium.webdriver.common.appiumby import AppiumBy
except ImportError:
    AppiumBy = None


class AngelOnePage(BaseTradingPage):
    @property
    def app_label(self) -> str:
        return "AngelOne"

    @property
    def package_name(self) -> str:
        return "com.msf.angelmobile"

    def enter_mpin(self, pin: str) -> bool:
        print(f"[*] [{self.app_label}] Unlocking with MPIN...")
        time.sleep(1.5)

        if self.driver and AppiumBy:
            try:
                for digit in pin:
                    xpath = f"//android.widget.TextView[@text='{digit}'] | //android.widget.Button[@text='{digit}']"
                    btn = self.driver.find_element(AppiumBy.XPATH, xpath)
                    btn.click()
                    time.sleep(0.15)
                time.sleep(2.0)
                return True
            except Exception as e:
                print(f"[-] [{self.app_label}] Custom pin error: {e}. Trying fallback...")

        self.gestures._run_adb_input(["text", pin])
        time.sleep(2.0)
        return True

    def navigate_to_watchlist(self) -> bool:
        print(f"[*] [{self.app_label}] Navigating to Watchlist...")
        if self.driver and AppiumBy:
            return self._click_or_ai_fallback(
                AppiumBy.XPATH,
                "//android.widget.TextView[contains(@text, 'Watchlist')] | //*[contains(@resource-id, 'tvWatchlist')]",
                "AngelOne Watchlist Tab"
            )
        self.gestures.tap_coordinates(self.gestures.screen_width // 5, int(self.gestures.screen_height * 0.95))
        return True

    def navigate_to_portfolio(self) -> bool:
        print(f"[*] [{self.app_label}] Navigating to Portfolio...")
        if self.driver and AppiumBy:
            return self._click_or_ai_fallback(
                AppiumBy.XPATH,
                "//android.widget.TextView[contains(@text, 'Portfolio')] | //*[contains(@resource-id, 'tvPortfolio')]",
                "AngelOne Portfolio Tab"
            )
        self.gestures.tap_coordinates(int(self.gestures.screen_width * 0.4), int(self.gestures.screen_height * 0.95))
        return True

    def navigate_to_positions(self) -> bool:
        print(f"[*] [{self.app_label}] Navigating to Orders / Positions...")
        if self.driver and AppiumBy:
            return self._click_or_ai_fallback(
                AppiumBy.XPATH,
                "//android.widget.TextView[contains(@text, 'Orders')] | //android.widget.TextView[contains(@text, 'Positions')] | //*[contains(@resource-id, 'tvOrders')]",
                "AngelOne Orders Tab"
            )
        self.gestures.tap_coordinates(int(self.gestures.screen_width * 0.6), int(self.gestures.screen_height * 0.95))
        return True

    def open_chart(self) -> bool:
        print(f"[*] [{self.app_label}] Opening Chart...")
        time.sleep(1.0)
        if self.driver and AppiumBy:
            # Tap first stock in list
            self._click_or_ai_fallback(
                AppiumBy.XPATH,
                "(//androidx.recyclerview.widget.RecyclerView//android.view.ViewGroup)[1]",
                "First Stock in List"
            )
            time.sleep(2.0)
            # Tap Chart icon / button
            self._click_or_ai_fallback(
                AppiumBy.XPATH,
                "//*[contains(@text, 'Charts')] | //*[contains(@content-desc, 'Chart')] | //*[contains(@resource-id, 'ivChart')]",
                "Charts View Button"
            )
            time.sleep(2.0)
            return True

        self.gestures.tap_coordinates(self.gestures.screen_width // 2, int(self.gestures.screen_height * 0.35))
        time.sleep(2.0)
        return True
