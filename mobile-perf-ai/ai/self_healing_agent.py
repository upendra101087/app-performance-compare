"""
Self-Healing AI Agent.
Recovers from unexpected blocking dialogs, promo modals, and minor UI redesigns
using Vision/DOM inspection with smart heuristic fallback.
"""

import json
import os
import re
from typing import Optional, Dict, Any

from ai.prompt_templates import SELF_HEALING_PROMPT

COMMON_DISMISS_PATTERNS = [
    r"(?i)\b(skip|not now|remind later|cancel|close|dismiss|later|maybe later|got it|continue)\b",
    r"(?i)\b(allow|while using the app|only this time)\b"
]


class SelfHealingAgent:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")

    def resolve_and_click(self, driver, target_description: str) -> bool:
        """
        Attempts to dismiss blocking dialogs or find the missing element.
        """
        try:
            page_source = driver.page_source
        except Exception:
            return False

        # 1. Try Fast Heuristic Rule Engine (Dismiss Popups)
        if self._try_heuristic_dismiss(driver, page_source):
            return True

        # 2. If API Key is present, invoke LLM
        if self.api_key:
            return self._invoke_llm_resolution(driver, page_source, target_description)

        return False

    def _try_heuristic_dismiss(self, driver, page_source: str) -> bool:
        from appium.webdriver.common.appiumby import AppiumBy

        for pattern in COMMON_DISMISS_PATTERNS:
            matches = re.findall(pattern, page_source)
            if matches:
                word = matches[0]
                try:
                    xpath = f"//android.widget.TextView[re:test(@text, '{word}', 'i')] | //android.widget.Button[re:test(@text, '{word}', 'i')]"
                    elem = driver.find_element(AppiumBy.XPATH, xpath)
                    print(f"[+] [AI Self-Heal] Dismissed blocking modal by tapping: '{word}'")
                    elem.click()
                    return True
                except Exception:
                    # Try simple text match
                    try:
                        elem = driver.find_element(AppiumBy.XPATH, f"//*[contains(translate(@text, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{word.lower()}')]")
                        print(f"[+] [AI Self-Heal] Dismissed blocking modal by tapping: '{word}'")
                        elem.click()
                        return True
                    except Exception:
                        pass
        return False

    def _invoke_llm_resolution(self, driver, page_source: str, target_description: str) -> bool:
        """
        Sends truncated page source to LLM to find the element or close dialog.
        """
        # Truncate source to avoid token limits
        snippet = page_source[:6000]
        prompt = SELF_HEALING_PROMPT.format(
            target_element=target_description,
            page_source_snippet=snippet
        )

        try:
            # Pluggable Gemini or OpenAI call
            # In mock or offline mode, falls back cleanly
            print(f"[*] [AI Self-Heal] Querying LLM for resolution of '{target_description}'...")
            # If Google GenAI library is present
            import urllib.request
            # If user has GEMINI_API_KEY set
            if os.getenv("GEMINI_API_KEY"):
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={os.getenv('GEMINI_API_KEY')}"
                payload = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")
                req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=8) as resp:
                    data = json.loads(resp.read().decode())
                    text_resp = data["candidates"][0]["content"]["parts"][0]["text"]
                    # Extract JSON
                    m = re.search(r"\{.*\}", text_resp, re.DOTALL)
                    if m:
                        decision = json.loads(m.group(0))
                        if decision.get("action") in ["dismiss_dialog", "click_target"] and decision.get("locator_value"):
                            from appium.webdriver.common.appiumby import AppiumBy
                            elem = driver.find_element(AppiumBy.XPATH, decision["locator_value"])
                            elem.click()
                            print(f"[+] [AI Self-Heal] LLM successfully resolved action: {decision.get('reasoning')}")
                            return True
        except Exception as e:
            print(f"[-] [AI Self-Heal] LLM call skipped or failed: {e}")

        return False
