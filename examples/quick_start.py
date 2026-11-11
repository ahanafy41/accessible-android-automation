#!/usr/bin/env python3
"""
Quickstart: Autonomous Chrome Automation on Android via CDP & Termux
Zero-PC, Zero-Root, Non-interfering with Screen Readers.
"""

import asyncio
import json
import urllib.request
import websockets

BASE_URL = "http://127.0.0.1:9222"

def get_browser_info():
    req = urllib.request.urlopen(f"{BASE_URL}/json/version")
    return json.loads(req.read().decode())

async def main():
    info = get_browser_info()
    print(f"Connected to: {info.get('Browser')}")
    browser_ws = info.get("webSocketDebuggerUrl")

    # 1. Create a clean tab silently via pure CDP
    async with websockets.connect(browser_ws) as bws:
        await bws.send(json.dumps({
            "id": 1,
            "method": "Target.createTarget",
            "params": {"url": "https://example.com"}
        }))
        res = json.loads(await bws.recv())
        target_id = res.get("result", {}).get("targetId")
        print(f"Created silent target: {target_id}")

    # 2. Give Chrome 0.5s to register
    await asyncio.sleep(0.5)

    # 3. Connect to page and evaluate DOM
    tabs = json.loads(urllib.request.urlopen(f"{BASE_URL}/json").read().decode())
    page = next((t for t in tabs if target_id in t.get("id", "") or target_id in t.get("webSocketDebuggerUrl", "")), None)
    
    if page:
        page_ws = page.get("webSocketDebuggerUrl")
        async with websockets.connect(page_ws) as pws:
            await pws.send(json.dumps({"id": 2, "method": "Page.enable"}))
            await pws.send(json.dumps({
                "id": 3,
                "method": "Runtime.evaluate",
                "params": {"expression": "document.title", "returnByValue": True}
            }))
            title_res = json.loads(await pws.recv())
            title = title_res.get("result", {}).get("result", {}).get("value")
            print(f"Page title extracted silently: '{title}'")

        # 4. Clean up: close the tab
        urllib.request.urlopen(f"{BASE_URL}/json/close/{page['id']}")
        print("Tab closed successfully. Device clean.")

if __name__ == "__main__":
    asyncio.run(main())
