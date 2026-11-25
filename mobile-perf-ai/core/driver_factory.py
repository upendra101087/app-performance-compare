"""
Driver Factory for Appium and Device Farm Connections.
Connects to local Appium servers or the Mac Mini Device Farm Hub (default port 31337 or 4723).
"""

from typing import Optional, Dict, Any
import subprocess

try:
    from appium import webdriver
    from appium.options.android import UiAutomator2Options
    APPIUM_AVAILABLE = True
except ImportError:
    APPIUM_AVAILABLE = False


class DriverFactory:
    @staticmethod
    def is_appium_available() -> bool:
        return APPIUM_AVAILABLE

    @staticmethod
    def create_driver(
        device_udid: str,
        package_name: str,
        hub_url: str = "http://127.0.0.1:4723",
        app_activity: Optional[str] = None,
        no_reset: bool = True
    ):
        """
        Initializes an Appium AndroidDriver session targeting the device.
        """
        if not APPIUM_AVAILABLE:
            raise RuntimeError(
                "Appium-Python-Client is not installed. Run 'pip install Appium-Python-Client' "
                "or run in ADB fallback mode."
            )

        options = UiAutomator2Options()
        options.platform_name = "Android"
        options.automation_name = "UiAutomator2"
        options.udid = device_udid
        options.app_package = package_name
        
        if app_activity:
            options.app_activity = app_activity
            
        options.no_reset = no_reset
        options.auto_grant_permissions = True
        options.set_capability("appium:skipUnlock", True)
        options.set_capability("appium:ignoreHiddenApiPolicyError", True)
        options.set_capability("appium:newCommandTimeout", 180)

        # Connect to Appium Hub / Local Server
        driver = webdriver.Remote(command_executor=hub_url, options=options)
        return driver
