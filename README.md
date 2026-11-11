# Accessible Android & Chrome Automation Protocol 🤖📱

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Android%20%7C%20Termux-green.svg)]()
[![Engine](https://img.shields.io/badge/Engine-Chrome%20DevTools%20Protocol%20(CDP)-orange.svg)]()
[![Assistive Tech](https://img.shields.io/badge/Accessibility-TalkBack%20%26%20Jieshuo%20Friendly-purple.svg)]()
[![Skill Standard](https://img.shields.io/badge/Skill%20Standard-writing--skills%20TDD-brightgreen.svg)]()

> **The definitive, production-tested protocol for autonomous browser and Android UI automation directly on-device inside Termux without requiring an external PC, root privileges, or physical USB cables.**

---

## 🌟 Why This Exists: Accessibility-First Philosophy

Most existing Android automation tools (Appium, UIAutomator2, PyAutoGUI, OpenCV wrappers) fail catastrophically on daily-driver mobile devices, especially for blind and visually impaired users relying on screen readers (**Google TalkBack** or **Jieshuo / Commentary Screen Reader**):

1. **The UIAutomator Freeze Bug:** Spammed calls to `uiautomator dump` lock Android's `AccessibilityManagerService` event queue. This freezes Text-to-Speech (TTS) audio and touch exploration for 1–3 seconds per query.
2. **The Floating Window Trap:** Tools launching Chrome in floating/pop-up windows (`--windowingMode 5`) create overlapping transparent window surfaces. This confuses Android's window hierarchy, traps accessibility focus, and breaks touch exploration muscle memory.
3. **Arabic & UTF-8 Text Corruption:** Standard `adb shell input text` corrupts non-ASCII characters, replacing Arabic letters and emojis with `???`.

### 🛡️ How This Protocol Solves It:
- **100% Blink-Engine Isolation:** Web content and accessibility trees are inspected internally via **Chrome DevTools Protocol (CDP)** and **ARIA AXTree (`Accessibility.getFullAXTree`)**. This bypasses Android's accessibility queue entirely—speech never stutters.
- **Strict Split-Screen / Background Mode:** Chrome runs either silently in the background via loopback or strictly in split-screen mode (`am stack move-task`). Floating windows are strictly banned.
- **Native UTF-8 Injection:** Text is dispatched via synthetic DOM `input` and `change` events in V8, ensuring 100% fidelity for Arabic, Unicode, and emojis.

---

## 🏗️ Architecture

```
   ┌─────────────────────────────────────────────────────────────┐
   │                      Android Device                         │
   │                                                             │
   │  ┌─────────────────────────┐   ┌─────────────────────────┐  │
   │  │    Termux Environment   │   │  Android Accessibility  │  │
   │  │  - Python Engine        │   │  - TalkBack / Jieshuo   │  │
   │  │  - Local ADB Client     │   │  - Uninterrupted Audio  │  │
   │  └───────────┬─────────────┘   └────────────▲────────────┘  │
   │              │                              │               │
   │        Local Loopback                 DO NOT LOCK           │
   │   (Port 5555 Permanent Mode)     (Bypass uiautomator)       │
   │              │                              │               │
   │  ┌───────────▼─────────────┐                │               │
   │  │   Android adbd Daemon   ├────────────────┘               │
   │  │  - Split Stacks (5 & 6) │                                │
   │  │  - Port 9222 Forward    │                                │
   │  └───────────┬─────────────┘                                │
   │              │                                              │
   │  ┌───────────▼───────────────────────────────────────────┐  │
   │  │    Google Chrome (Split-Screen Kept Alive)            │  │
   │  │   - Abstract Socket: @chrome_devtools_remote          │  │
   │  │   - CDP (DOM, ARIA AXTree, Network, Runtime, Page)    │  │
   │  └───────────────────────────────────────────────────────┘  │
   └─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Setup Guide (On-Device from Scratch)

### 1. Requirements inside Termux
```bash
pkg update && pkg install -y git python android-tools
pip install websockets
```

### 2. Enable Wireless Debugging
1. Open Android **Settings** > **About phone** > tap **Build number** 7 times.
2. In **Developer Options**, turn ON:
   - **USB debugging**
   - **Wireless debugging**

### 3. One-Shot Permanent Port 5555 Binding
You only need to pair once per Wi-Fi network. After binding to port 5555, **ADB stays connected via local loopback even if Wi-Fi is disconnected or Wireless Debugging is turned OFF in Settings!**

```bash
# First time pairing:
bash scripts/setup_wireless_adb.sh <IP:PORT> <PAIRING_CODE>

# Subsequent reconnects:
adb connect 127.0.0.1:5555
```

### 4. Forward Chrome DevTools Socket
```bash
# Whitelist Chrome from battery killers
adb -s 127.0.0.1:5555 shell dumpsys deviceidle whitelist +com.android.chrome

# Forward local port 9222 to Chrome's abstract unix socket
adb -s 127.0.0.1:5555 forward tcp:9222 localabstract:chrome_devtools_remote

# Verify connection
curl -s http://127.0.0.1:9222/json/version
```

---

## 💻 Python Automation Examples

### 1. Silent New Tab Creation (Pure CDP)
Unlike desktop Chrome, Chrome on Android restricts the HTTP endpoint `/json/new`. Use pure CDP `Target.createTarget` on the browser WebSocket instead:

```python
import asyncio, json, urllib.request, websockets

async def create_silent_tab(url="https://example.com"):
    version = json.loads(urllib.request.urlopen("http://127.0.0.1:9222/json/version").read().decode())
    browser_ws = version["webSocketDebuggerUrl"]

    async with websockets.connect(browser_ws) as ws:
        await ws.send(json.dumps({
            "id": 1,
            "method": "Target.createTarget",
            "params": {"url": url}
        }))
        res = json.loads(await ws.recv())
        return res["result"]["targetId"]

asyncio.run(create_silent_tab())
```

### 2. Arabic & UTF-8 Form Filling + Synthetic Clicks
```python
# See examples/fill_arabic_form.py
from examples.fill_arabic_form import inject_arabic_input, safe_synthetic_click

# Safely types Arabic text with instant reactive framework change dispatch
await inject_arabic_input(page_ws, "#username", "أحمد - تجربة الأتمتة الميسرة 2026 🚀")

# Dispatches pointerdown -> mousedown -> pointerup -> mouseup -> click
await safe_synthetic_click(page_ws, "#submit-btn")
```

### 3. Screen-Reader Native ARIA Accessibility Tree Inspection
```python
# See examples/scrape_semantic_table.py
from examples.scrape_semantic_table import get_aria_tree

# Fetches full semantic tree (role, name, value) without uiautomator freeze
nodes = await get_aria_tree(page_ws)
for node in nodes:
    print(f"Role: {node.get('role', {}).get('value')} | Label: {node.get('name', {}).get('value')}")
```

---

## 🪟 Definitive Split-Screen Execution (AOSP & Samsung One UI)

On modern Samsung One UI (One UI 5/6/7 on Android 13/14/15), standard shell `--windowingMode 4` flags are intercepted and forced into fullscreen. 

To reliably divide the screen without floating window focus bleed, this protocol moves running tasks directly into Android's Split-Screen Stacks:

```bash
bash scripts/split_screen_manager.sh
```

Or manually:
```bash
# Move Chrome to Primary Split (Top Half - Stack 5)
adb -s 127.0.0.1:5555 shell am stack move-task <CHROME_TASK_ID> 5 true

# Move Termux / Companion to Secondary Split (Bottom Half - Stack 6)
adb -s 127.0.0.1:5555 shell am stack move-task <APP_TASK_ID> 6 true
```

---

## 🧪 Verification & Self-Healing Protocol

This skill strictly enforces the **`writing-skills` TDD standard (RED - GREEN - REFACTOR)**:
- Whenever a runtime error or new OEM restriction is encountered, it must be captured in `scratch/`, forensically analyzed (`dumpsys`, unix sockets), verified with a 100% pass test harness, and atomically patched into `SKILL.md`.
- **Lean Maintenance Policy:** `SKILL.md` enforces a strict token budget (< 650 lines), pruning obsolete workarounds and keeping the active troubleshooting table capped at 10 high-value rows.

### Run Verification Suite
```bash
python3 scripts/test_accessible_automation.py
```
*Executes all 9 end-to-end tests (tab creation, DOM injection, Arabic UTF-8 integrity, synthetic clicks, ARIA AXTree retrieval, clean scraping, desktop mode emulation, and tab cleanup) in ~5 seconds directly on-device.*

---

## 📖 نظرة سريعة بالعربية (Arabic Summary)

هذا المستودع يحتوي على بروتوكول الأتمتة الميسرة لمتصفح جوجل كروم ونظام أندرويد من داخل تطبيق **Termux** مباشرة بدون روت وبدون الحاجة لجهاز كمبيوتر خارجي.

- **الأولوية المطلقة لإمكانية الوصول**: تم تصميم البروتوكول خصيصاً لمستخدمي قارئات الشاشة (TalkBack وقارئ الشاشة الصيني Jieshuo)، حيث يعتمد بنسبة 100% على بروتوكول **Chrome DevTools Protocol (CDP)** وشجرة الوصول الداخلية **ARIA AXTree** بدلاً من أوامر فحص الشاشة التقليدية التي تسبب تعليق ونحنحة الصوت.
- **حظر النوافذ العائمة**: حظر قاطع للنوافذ المنبثقة واستبدالها بنظام تقسيم الشاشة الثابت (`am stack move-task`).
- **سلامة اللغة العربية**: حقن النصوص العربية والإيموجي بالكامل عبر أحداث V8 التفاعلية دون تشويه الحروف.
- **الاتصال الدائم 5555**: اتصال محلي داخلي سريع ومستقر حتى لو تم إيقاف تصحيح الأخطاء اللاسلكي أو فصل الواي فاي.

---

## 📄 License

Distributed under the [MIT License](LICENSE).  
Authored by **Ahmed Hanafy** ([@ahanafy41](https://github.com/ahanafy41)).
