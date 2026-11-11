#!/usr/bin/env python3
"""
Arabic & UTF-8 Form Filling + Safe Synthetic Clicks
Zero input text corruption, zero accessibility focus disruption.
"""

import asyncio
import json
import websockets

async def inject_arabic_input(page_ws, input_selector, arabic_text):
    """Safely sets input value and dispatches reactive events (input/change)."""
    js_code = f"""
    (() => {{
        const el = document.querySelector({json.dumps(input_selector)});
        if (!el) return false;
        el.focus();
        el.value = {json.dumps(arabic_text)};
        el.dispatchEvent(new Event('input', {{ bubbles: true }}));
        el.dispatchEvent(new Event('change', {{ bubbles: true }}));
        return el.value;
    }})()
    """
    async with websockets.connect(page_ws) as ws:
        await ws.send(json.dumps({
            "id": 1,
            "method": "Runtime.evaluate",
            "params": {"expression": js_code, "returnByValue": True}
        }))
        res = json.loads(await ws.recv())
        return res.get("result", {}).get("result", {}).get("value")

async def safe_synthetic_click(page_ws, button_selector):
    """Triggers pointer down/up/click events without touch exploration lock."""
    js_code = f"""
    (() => {{
        const btn = document.querySelector({json.dumps(button_selector)});
        if (!btn) return false;
        btn.scrollIntoView({{ behavior: 'instant', block: 'center' }});
        ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'].forEach(evt => {{
            btn.dispatchEvent(new MouseEvent(evt, {{ bubbles: true, cancelable: true, view: window }}));
        }});
        return true;
    }})()
    """
    async with websockets.connect(page_ws) as ws:
        await ws.send(json.dumps({
            "id": 2,
            "method": "Runtime.evaluate",
            "params": {"expression": js_code, "returnByValue": True}
        }))
        res = json.loads(await ws.recv())
        return res.get("result", {}).get("result", {}).get("value")

if __name__ == "__main__":
    print("Helper module for Arabic/UTF-8 input and safe pointer clicks.")
