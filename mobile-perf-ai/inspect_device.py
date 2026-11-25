#!/usr/bin/env python3
"""
Interactive UI Hierarchy & Locator Inspector.
Connects to an attached real Android device or emulator,
dumps the active screen's UI hierarchy, and prints clean, ready-to-use locators
(Resource IDs, Accessibility IDs, Text, and XPaths) for Page Objects.

Usage:
    python3 inspect_device.py                # Inspects the current screen
    python3 inspect_device.py --screenshot   # Also saves a screenshot to screen.png
    python3 inspect_device.py --filter watch # Filters elements containing 'watch'
"""

import argparse
import subprocess
import sys
import xml.etree.ElementTree as ET
from typing import List, Dict, Any


def get_connected_device() -> str:
    res = subprocess.run(["adb", "devices"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    for line in res.stdout.strip().splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            return parts[0]
    return ""


def dump_screen_hierarchy(device_udid: str) -> str:
    # Dump hierarchy to /sdcard/dump.xml and cat it
    subprocess.run(["adb", "-s", device_udid, "shell", "uiautomator", "dump", "/sdcard/dump.xml"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    res = subprocess.run(["adb", "-s", device_udid, "shell", "cat", "/sdcard/dump.xml"],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return res.stdout.strip()


def parse_and_display_locators(xml_content: str, filter_keyword: str = ""):
    if not xml_content or "<hierarchy" not in xml_content:
        print("[-] Error: Unable to retrieve window dump from device.")
        return

    try:
        root = ET.fromstring(xml_content)
    except Exception as e:
        print(f"[-] XML parse error: {e}")
        return

    elements: List[Dict[str, Any]] = []
    
    for node in root.iter("node"):
        text = node.attrib.get("text", "").strip()
        res_id = node.attrib.get("resource-id", "").strip()
        desc = node.attrib.get("content-desc", "").strip()
        cls_name = node.attrib.get("class", "").strip()
        clickable = node.attrib.get("clickable", "false") == "true"
        bounds = node.attrib.get("bounds", "")

        # Skip empty container nodes unless clickable
        if not text and not res_id and not desc:
            continue

        item = {
            "text": text,
            "resource_id": res_id,
            "content_desc": desc,
            "class": cls_name,
            "clickable": clickable,
            "bounds": bounds
        }

        # Apply filter if provided
        if filter_keyword:
            kw = filter_keyword.lower()
            if kw not in text.lower() and kw not in res_id.lower() and kw not in desc.lower():
                continue

        elements.append(item)

    print("\n" + "="*110)
    print(f"📍 DETECTED UI ELEMENTS ({len(elements)} found)")
    print("="*110)
    print(f"{'Class / Type':<25} | {'Text':<25} | {'Resource ID':<35} | {'Accessibility ID'}")
    print("-" * 110)

    for el in elements:
        cls_short = el["class"].split(".")[-1]
        text_disp = (el["text"][:22] + "...") if len(el["text"]) > 25 else el["text"]
        id_disp = (el["resource_id"][:32] + "...") if len(el["resource_id"]) > 35 else el["resource_id"]
        desc_disp = el["content_desc"]
        click_mark = "👆 " if el["clickable"] else "   "
        print(f"{click_mark}{cls_short:<22} | {text_disp:<25} | {id_disp:<35} | {desc_disp}")

    print("="*110)
    print("\n💡 Suggested Locators for Page Objects:")
    for el in elements[:12]:
        if el["resource_id"]:
            print(f"  • By ID:      AppiumBy.ID, \"{el['resource_id']}\"")
        elif el["text"]:
            print(f"  • By XPath:   AppiumBy.XPATH, \"//{el['class']}[@text='{el['text']}']\"")
        elif el["content_desc"]:
            print(f"  • By Acc ID:  AppiumBy.ACCESSIBILITY_ID, \"{el['content_desc']}\"")
    print()


def main():
    parser = argparse.ArgumentParser(description="Live Android UI Locator Inspector")
    parser.add_argument("--device", help="Target device UDID")
    parser.add_argument("--filter", default="", help="Filter elements by keyword (e.g. 'Watchlist', '1', 'Chart')")
    parser.add_argument("--screenshot", action="store_true", help="Save current screen to screenshot.png")
    args = parser.parse_args()

    device = args.device or get_connected_device()
    if not device:
        print("[-] No connected Android device found via ADB.")
        sys.exit(1)

    print(f"[+] Target Device: {device}")
    
    if args.screenshot:
        subprocess.run(["adb", "-s", device, "exec-out", "screencap", "-p"], stdout=open("screenshot.png", "wb"))
        print("[+] Screen capture saved to: screenshot.png")

    xml_data = dump_screen_hierarchy(device)
    parse_and_display_locators(xml_data, filter_keyword=args.filter)


if __name__ == "__main__":
    main()
