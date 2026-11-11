#!/usr/bin/env python3
"""
ARIA Accessibility Tree Inspection & Clean Structured Scraping
Reads page semantics via Blink V8 engine without locking Android AccessibilityService.
"""

import asyncio
import json
import websockets

async def get_aria_tree(page_ws):
    """Fetches the internal Chromium Accessibility Tree (Bypassing uiautomator)."""
    async with websockets.connect(page_ws) as ws:
        await ws.send(json.dumps({"id": 1, "method": "Accessibility.enable"}))
        await ws.recv()
        await ws.send(json.dumps({"id": 2, "method": "Accessibility.getFullAXTree"}))
        res = json.loads(await ws.recv())
        return res.get("result", {}).get("nodes", [])

async def scrape_table(page_ws, table_selector):
    """Extracts 2D array of clean text from HTML table."""
    js_code = f"""
    (() => {{
        const rows = Array.from(document.querySelectorAll('{table_selector} tr'));
        return rows.map(r => Array.from(r.querySelectorAll('th, td')).map(c => c.innerText.trim()));
    }})()
    """
    async with websockets.connect(page_ws) as ws:
        await ws.send(json.dumps({
            "id": 3,
            "method": "Runtime.evaluate",
            "params": {"expression": js_code, "returnByValue": True}
        }))
        res = json.loads(await ws.recv())
        return res.get("result", {}).get("result", {}).get("value")

if __name__ == "__main__":
    print("Helper module for ARIA AXTree and clean table scraping.")
