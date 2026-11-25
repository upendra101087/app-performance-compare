"""
Groww App Page Object (com.nextbillion.groww).
Encapsulates navigation, custom in-app MPIN keypad interactions,
watchlist tabs, and chart viewing.
"""

import time
from pages.base_trading_page import BaseTradingPage

try:
    from appium.webdriver.common.appiumby import AppiumBy
except ImportError:
    AppiumBy = None


class GrowwPage(BaseTradingPage):
    @property
    def app_label(self) -> str:
        return "Groww"

    @property
    def package_name(self) -> str:
        return "com.nextbillion.groww"

    def enter_mpin(self, pin: str) -> bool:
        """
        Enters 4-digit MPIN on Groww's in-app numeric pad.
        """
        print(f"[*] [{self.app_label}] Unlocking with MPIN...")
        time.sleep(1.5)  # Let lock screen render

        if self.driver and AppiumBy:
            try:
                for digit in pin:
                    # Target keypad buttons
                    xpath = f"//android.widget.TextView[@text='{digit}'] | //android.widget.Button[@text='{digit}']"
                    btn = self.driver.find_element(AppiumBy.XPATH, xpath)
                    btn.click()
                    time.sleep(0.15)
                time.sleep(2.0)
                return True
            except Exception as e:
                print(f"[-] [{self.app_label}] Keypad locator error: {e}. Trying fallback...")

        # Fallback: ADB text input
        self.gestures._run_adb_input(["text", pin])
        time.sleep(2.0)
        return True

    def navigate_to_watchlist(self) -> bool:
        print(f"[*] [{self.app_label}] Navigating to Watchlist...")
        if self.driver and AppiumBy:
            return self._click_or_ai_fallback(
                AppiumBy.XPATH,
                "//android.widget.TextView[contains(@text, 'Watchlist')] | //*[@content-desc='Watchlist'] | //*[contains(@resource-id, 'watchlist')]",
                "Groww Watchlist Tab"
            )
        # Fallback coordinate tap on standard bottom nav bar (2nd tab)
        self.gestures.tap_coordinates(self.gestures.screen_width // 4, int(self.gestures.screen_height * 0.95))
        return True

    def navigate_to_portfolio(self) -> bool:
        print(f"[*] [{self.app_label}] Navigating to Portfolio / Holdings...")
        if self.driver and AppiumBy:
            return self._click_or_ai_fallback(
                AppiumBy.XPATH,
                "//android.widget.TextView[contains(@text, 'Holdings')] | //android.widget.TextView[contains(@text, 'Portfolio')] | //*[contains(@resource-id, 'holdings')]",
                "Groww Portfolio Tab"
            )
        # Fallback coordinate tap (3rd tab)
        self.gestures.tap_coordinates(int(self.gestures.screen_width * 0.5), int(self.gestures.screen_height * 0.95))
        return True

    def navigate_to_positions(self) -> bool:
        print(f"[*] [{self.app_label}] Navigating to Positions / Orders...")
        if self.driver and AppiumBy:
            return self._click_or_ai_fallback(
                AppiumBy.XPATH,
                "//android.widget.TextView[contains(@text, 'Positions')] | //android.widget.TextView[contains(@text, 'Orders')] | //*[contains(@resource-id, 'orders')]",
                "Groww Orders/Positions Tab"
            )
        # Fallback coordinate tap (4th tab)
        self.gestures.tap_coordinates(int(self.gestures.screen_width * 0.75), int(self.gestures.screen_height * 0.95))
        return True

    def open_chart(self) -> bool:
        print(f"[*] [{self.app_label}] Opening Candlestick Chart...")
        time.sleep(1.0)
        # 1. Tap first stock in current list
        if self.driver and AppiumBy:
            clicked = self._click_or_ai_fallback(
                AppiumBy.XPATH,
                "(//android.widget.ScrollView//android.view.ViewGroup)[1] | (//androidx.recyclerview.widget.RecyclerView//android.view.ViewGroup)[1]",
                "First Stock in List"
            )
            time.sleep(2.0)
            # 2. Tap chart icon
            self._click_or_ai_fallback(
                AppiumBy.XPATH,
                "//*[contains(@content-desc, 'chart')] | //*[contains(@resource-id, 'chart')] | //android.widget.ImageView[contains(@content-desc, 'Chart')]",
                "Candlestick Chart Button"
            )
            time.sleep(2.0)
            return True
            
        # Fallback tap top item then chart area
        self.gestures.tap_coordinates(self.gestures.screen_width // 2, int(self.gestures.screen_height * 0.35))
        time.sleep(2.0)
        return True
