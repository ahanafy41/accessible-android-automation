---
name: accessible-android-automation
description: Use when automating mobile Chrome or web tasks on Android from Termux, controlling browser tabs via Chrome DevTools Protocol (CDP), inspecting web pages via ARIA accessibility tree without freezing TalkBack or Jieshuo, setting up wireless ADB from scratch on-device, or keeping browser processes alive using split-screen mode.
---

# Accessible Android & Chrome Automation Protocol

## 1. Overview & Core Philosophy

This skill defines the definitive, production-tested protocol for autonomous **Browser and Android UI Automation** running directly **on-device inside Termux** without requiring an external PC, root privileges, or physical USB cables.

The architecture prioritizes **Chrome DevTools Protocol (CDP)** as the primary automation engine, backed by **On-Device Wireless ADB** as the transport layer.

```
   ┌─────────────────────────────────────────────────────────────┐
   │                      Android Device                         │
   │                                                             │
   │  ┌─────────────────────────┐   ┌─────────────────────────┐  │
   │  │    Termux Environment   │   │  Android Accessibility  │  │
   │  │  - Python / Node Engine │   │  - TalkBack / Jieshuo   │  │
   │  │  - Local ADB Client     │   │  - Uninterrupted Audio  │  │
   │  └───────────┬─────────────┘   └────────────▲────────────┘  │
   │              │                              │               │
   │        Local Loopback                 DO NOT LOCK           │
   │   (Port 5555 Permanent Mode)     (Bypass uiautomator)       │
   │              │                              │               │
   │  ┌───────────▼─────────────┐                │               │
   │  │   Android adbd Daemon   ├────────────────┘               │
   │  │  - Split-Screen Mode    │                                │
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

## 2. When to Use

### Use this skill when:
- Automating web browsing, form filling, or content scraping on Android directly from Termux.
- Managing Chrome tabs silently in the background without pulling the browser over the user's active window.
- Extracting semantic web page elements using the internal ARIA accessibility tree rather than brittle visual OCR.
- Setting up on-device Wireless ADB from absolute scratch (enabling developer options, pairing code, and permanent port 5555).
- Preventing Android OEM battery optimization from suspending Chrome during automation using split-screen mode.
- Ensuring automation never interrupts, stutters, or freezes screen readers (TalkBack / Jieshuo).

### When NOT to use:
- Building native Android apps or compiling APKs (use `android-cli` or Gradle instead).
- Pure backend or command-line scripting that does not involve an Android browser or UI.
- Desktop Chrome automation on standard Linux/macOS/Windows machines (standard Playwright/Puppeteer applies there).

---

## 3. Invariants & Golden Rules

1. **Accessibility-First Non-Interference Invariant:**
   - Automation routines must NEVER freeze, lock, choke, or interrupt active assistive technologies (TalkBack or Jieshuo / Commentary Screen Reader).
   - NEVER spam or loop `uiautomator dump`. Traversal locks Android's `AccessibilityManagerService` event queue, cutting off TTS speech and touch exploration for 1–3 seconds per call.
   - For web content: Rely 100% on **Chrome DevTools Protocol (CDP)** and the internal web **ARIA Accessibility Tree (`Accessibility.getFullAXTree`)**. This runs entirely inside the Chromium engine without touching Android's accessibility queue.
2. **Persistent Visible Mode Invariant (Split-Screen Only - Strict Floating Window Ban):**
   - Android OEMs (especially Samsung One UI, Xiaomi MIUI, ColorOS) aggressively freeze or kill background browser renderers and drop the DevTools socket.
   - When automating Chrome: Keep Chrome visible on screen **exclusively in Split-Screen Mode (`--windowingMode 4`)** adjacent to Termux/Antigravity.
   - **DO NOT use Floating / Pop-Up View (`--windowingMode 5`)**: Floating windows create severe accessibility barriers for screen readers (TalkBack / Jieshuo). They create overlapping window layers that trap accessibility focus, cause erratic focus jumping between background and foreground, and collide with touch exploration coordinates. Split-Screen maintains clear, separate, non-overlapping window regions natively supported by accessibility services.
3. **Permanent Port 5555 Invariant (No Dynamic Port Churn):**
   - Android 11+ dynamic wireless debugging ports expire after idle periods or Wi-Fi reconnects.
   - Once connected to any dynamic port, promote the connection immediately to permanent mode via `adb tcpip 5555`, then bind to `127.0.0.1:5555`. This connection persists across idle periods until device reboot.
4. **Arabic & UTF-8 Text Integrity Invariant:**
   - Android's native `input text` command corrupts or drops non-ASCII characters (Arabic, emojis, accented letters).
   - For web forms: Always inject text via CDP `Runtime.evaluate` with synthetic DOM events (`input`, `change`).
   - For native fallbacks: Use system clipboard broadcasting (`termux-clipboard-set` + Keyevent 279) or URL-encoded deep link intents.

---

## 4. Phase 0: Zero-to-Hero ADB Setup Guide (دليل التفعيل من الصفر)

If Wireless Debugging or ADB is not configured or enabled yet, guide the user step-by-step through this zero-friction onboarding flow. All steps are optimized for screen reader users (TalkBack / Jieshuo).

### Step 1: Enable Developer Options (تفعيل خيارات المطور)
1. Open Android Settings:
   - Direct Termux command: `am start -a android.settings.DEVICE_INFO_SETTINGS`
   - Or manually: Open **Settings** > **About phone** > **Software information**.
2. Locate **Build number** (رقم الإصدار).
3. Tap **Build number** 7 times rapidly. Enter lock screen PIN/pattern if prompted.
4. Screen reader will announce: *"You are now a developer!"* (أصبحت الآن مطور برامج).

### Step 2: Open Developer Options & Enable Wireless Debugging
1. Open Developer Options directly from Termux:
   ```bash
   am start -a android.settings.APPLICATION_DEVELOPMENT_SETTINGS
   ```
2. Scroll / swipe to find:
   - **USB debugging** (تصحيح أخطاء USB): Turn **ON**.
   - **Wireless debugging** (تصحيح الأخطاء اللاسلكي): Turn **ON**.
   *(Make sure the phone is connected to Wi-Fi).*
3. If a permission dialog appears: Check "Always allow on this network" and tap **Allow** (سماح).

### Step 3: Pair for the First Time (الإقران لأول مرة)
*(Note: Pairing is required only ONCE per Wi-Fi network).*

1. Inside **Wireless debugging**, tap on:
   **Pair device with pairing code** (إقران الجهاز باستخدام رمز إقران).
2. A popup dialog will display two pieces of info:
   - **Wi-Fi pairing code** (رمز إقران المكون من 6 أرقام، مثلاً: `829143`).
   - **IP address & Port** (عنوان IP والمنفذ، مثلاً: `192.168.1.5:37563`).
3. Switch to Termux and run the pairing command:
   ```bash
   adb pair <IP>:<PORT> <CODE>
   # مثال:
   adb pair 192.168.1.5:37563 829143
   ```
4. Verification: Terminal outputs `Successfully paired to 192.168.1.5:37563`.

### Step 4: Initial Connection & Permanent 5555 Promotion (الاتصال الدائم)
1. Dismiss the pairing popup. Look at the main **Wireless debugging** screen under "IP address & Port" to see the active dynamic connection port (e.g., `192.168.1.5:43309`).
2. Run this 4-step permanent binding sequence in Termux:
   ```bash
   # 1. Connect to dynamic port
   adb connect 192.168.1.5:<DYNAMIC_PORT>

   # 2. Promote adbd to permanent port 5555
   adb -s 192.168.1.5:<DYNAMIC_PORT> tcpip 5555

   # 3. Connect to local loopback permanent port
   sleep 1
   adb connect 127.0.0.1:5555

   # 4. Disconnect dynamic session to prevent duplicate devices
   adb disconnect 192.168.1.5:<DYNAMIC_PORT>
   ```
3. Test status:
   ```bash
   adb devices
   # Should cleanly list: 127.0.0.1:5555 device
   ```

*(From now on, the device remains reachable via `127.0.0.1:5555` even if Wireless Debugging dynamic ports toggle off, until the phone is restarted).*

---

## 5. Phase 1: Browser Keep-Alive & Multi-Window Architecture

To prevent Android and OEM task killers from killing Chrome, suspending its V8 JavaScript engine, or closing `@chrome_devtools_remote`, keep Chrome active in a dedicated windowing mode.

### 5.1 When & How to Use Split-Screen Mode (تقسيم الشاشة: متى وكيف؟)

Split-Screen Mode is NOT always mandatory for simple scraping or background tab reading. However, **certain websites strictly require the browser window to be visible on screen before enabling buttons or rendering content**:
1. **Page Visibility API Gates:** Sites checking `document.visibilityState === 'visible'` before enabling "Next", "Submit", or countdown timers.
2. **IntersectionObserver & Lazy Rendering:** Web apps where interactive buttons or forms only render when physically intersecting the active device viewport.
3. **Bot Detection & Viewability Verification:** Services that verify the window is actively painted by the OS display compositor.

> [!WARNING]
> **Modern OEM & Samsung One UI Windowing Restriction:**
> On pure AOSP/Android, launching Primary (`--windowingMode 3`) and Secondary (`--windowingMode 4`) splits the display automatically.
> However, on **Samsung One UI (One UI 5/6, Android 13/14+)**, Samsung's `StageCoordinator` restricts shell-initiated split-screen and defaults `--windowingMode 4` to full-screen unless split-screen was initiated via the Recents UI.
> **Universal Solution:**
> 1. Always try **Pattern D (Headless Page Visibility Bypass)** first—it works 100% silently inside Chromium without opening any windows!
> 2. If physical rendering is strictly enforced by the site, use **Quick Bring-to-Front with Auto-Return** (brings Chrome to front for 0.5s, triggers the click, then immediately restores the companion/Termux app).

#### Definitive Split-Screen Command (Works on AOSP & Samsung One UI):
While `am start --windowingMode` may be intercepted by OEM task organizers when apps are already running, moving the tasks directly into Android's Split-Screen Stacks via `am stack move-task` works 100% reliably:
```bash
# 1. Query running Task IDs
CHROME_TASK=$(adb -s 127.0.0.1:5555 shell "dumpsys activity recents | grep -B 1 'realActivity=.*com.android.chrome' | grep -oE 'taskId=[0-9]+' | head -n 1 | cut -d= -f2")
APP_TASK=$(adb -s 127.0.0.1:5555 shell "dumpsys activity recents | grep -B 1 'realActivity=.*com.antigravity.companion' | grep -oE 'taskId=[0-9]+' | head -n 1 | cut -d= -f2")

# 2. Find Split Stack IDs (usually 5 for primary top, 6 for secondary bottom)
# adb -s 127.0.0.1:5555 shell "am stack list"

# 3. Move Chrome to Top Half (Primary Split) and Companion/Termux to Bottom Half (Secondary Split)
adb -s 127.0.0.1:5555 shell am stack move-task $CHROME_TASK 5 true
adb -s 127.0.0.1:5555 shell am stack move-task $APP_TASK 6 true
```

#### Bringing the Target Tab to Active Viewport:
When Chrome is in split-screen, bring the exact target tab into active view via CDP:
```python
# 1. Activate tab inside Chrome
await chrome.send_cdp(browser_ws, "Target.activateTarget", {"targetId": target_id})
# 2. Tell page to bring its frame to front
await chrome.send_cdp(page_ws, "Page.bringToFront")
```

### 5.2 Strict Prohibition: Floating / Pop-Up View (حظر النوافذ العائمة تماماً)
**DO NOT USE `--windowingMode 5` (Samsung Pop-up View / Freeform).**
Floating windows create major usability breakdowns for screen reader users (TalkBack / Jieshuo / CSR):
1. **Focus Bleed & Trapping:** Assistive touch exploration and swipe navigation frequently slip between the floating window and the app underneath, trapping the cursor or reading elements out of order.
2. **Ambiguous Window Hierarchy:** Android AccessibilityService struggles to delineate clear semantic boundaries for freeform floating overlays, resulting in confusing spoken announcements.
3. **Touch Exploration Obstruction:** Floating frames cover background interactive areas without dismissing them, disrupting physical gesture muscle memory.
**Rule:** Always enforce Split-Screen (`--windowingMode 4`), never Pop-up (`--windowingMode 5`).

### 5.3 Battery Exemption Whitelist (درع حماية البطارية)
Prevent Doze mode from freezing Chrome during long background tasks:
```bash
adb -s 127.0.0.1:5555 shell dumpsys deviceidle whitelist +com.android.chrome
```

### 5.4 Chrome Process Verification & Auto-Wake
If Chrome ever gets paused or suspended:
```bash
# Check if Chrome process is alive
adb -s 127.0.0.1:5555 shell "ps -A | grep -i com.android.chrome"

# If dead or stopped, revive cleanly in Split-Screen without losing user position
adb -s 127.0.0.1:5555 shell am start -n com.android.chrome/com.google.android.apps.chrome.Main --windowingMode 4
```

---

## 6. Phase 2: Chrome DevTools Protocol (CDP) Bridge & Tab Management

### 6.1 Establishing the DevTools Port Forward
Forward local port 9222 to Chrome's abstract unix domain socket:
```bash
adb -s 127.0.0.1:5555 forward tcp:9222 localabstract:chrome_devtools_remote
```

Verify connection:
```bash
curl -s http://127.0.0.1:9222/json/version
```

### 6.2 Tab Management: CDP WebSocket vs HTTP Endpoints

> [!IMPORTANT]
> **Android Chrome Tab Creation Nuance:**
> Unlike desktop Chrome, Chrome on Android disables the HTTP endpoint `/json/new` (returning `Could not create new page` or 500 error) for sandboxing reasons.
> To open new tabs cleanly and silently without UI interruptions:
> 1. **Pure CDP (Recommended):** Connect to `browserWebSocketUrl` (obtained from `/json/version`) and call `Target.createTarget({"url": "<URL>"})`.
> 2. **Native Intent Fallback:** Run `am start -a android.intent.action.VIEW -d "<URL>" -n com.android.chrome/com.google.android.apps.chrome.Main --windowingMode 4`.

| Action | Method | Description |
|---|---|---|
| **List Tabs** | `curl -s http://127.0.0.1:9222/json` | Returns JSON array of all open tabs with `id`, `url`, `title`, and `webSocketDebuggerUrl`. |
| **New Tab (CDP)** | Browser WS: `Target.createTarget` | Opens a new tab silently and returns `targetId`. Zero UI flicker or interruption. |
| **Activate Tab** | `curl -s "http://127.0.0.1:9222/json/activate/<TARGET_ID>"` | Or CDP `Target.activateTarget`. Brings specified tab to active focus. |
| **Close Tab** | `curl -s "http://127.0.0.1:9222/json/close/<TARGET_ID>"` | Or CDP `Target.closeTarget`. Closes specified tab cleanly. |
| **Browser Version** | `curl -s http://127.0.0.1:9222/json/version` | Returns Chromium version, V8 version, and `webSocketDebuggerUrl`. |

---

## 7. Phase 3: CDP Automation Engine & DOM Interaction

### 7.1 Lightweight Async Python CDP Client
No heavy dependencies needed. Standard `websockets` (or Python `urllib` + `asyncio`) executes commands with sub-millisecond latency.

```python
import asyncio
import json
import urllib.request
import websockets

class ChromeController:
    def __init__(self, host="127.0.0.1", port=9222):
        self.base_url = f"http://{host}:{port}"
        self.msg_id = 0

    def list_tabs(self):
        req = urllib.request.urlopen(f"{self.base_url}/json")
        return json.loads(req.read().decode())

    def get_browser_ws(self):
        req = urllib.request.urlopen(f"{self.base_url}/json/version")
        return json.loads(req.read().decode())["webSocketDebuggerUrl"]

    async def new_tab(self, url="about:blank"):
        browser_ws = self.get_browser_ws()
        res = await self.send_cdp(browser_ws, "Target.createTarget", {"url": url})
        target_id = res.get("targetId")
        # Give Chrome a brief moment to register
        await asyncio.sleep(0.3)
        tabs = self.list_tabs()
        return next((t for t in tabs if target_id in t.get("id", "") or target_id in t.get("webSocketDebuggerUrl", "")), {"id": target_id})

    def close_tab(self, tab_id):
        urllib.request.urlopen(f"{self.base_url}/json/close/{tab_id}")

    async def send_cdp(self, ws_url, method, params=None):
        self.msg_id += 1
        payload = {"id": self.msg_id, "method": method, "params": params or {}}
        async with websockets.connect(ws_url, max_size=10_000_000) as ws:
            await ws.send(json.dumps(payload))
            while True:
                res = json.loads(await ws.recv())
                if res.get("id") == payload["id"]:
                    return res.get("result", {})

    async def evaluate(self, ws_url, js_expr):
        result = await self.send_cdp(ws_url, "Runtime.evaluate", {
            "expression": js_expr,
            "returnByValue": True,
            "awaitPromise": True
        })
        return result.get("result", {}).get("value")
```

---

### 7.2 ARIA Accessibility Tree Inspection (Screen-Reader Native)
Rather than guessing screen coordinates, query the internal browser Accessibility Tree via CDP:

```python
async def get_accessibility_tree(chrome, ws_url):
    # Enables accessibility domain and fetches complete semantic tree
    await chrome.send_cdp(ws_url, "Accessibility.enable")
    ax_tree = await chrome.send_cdp(ws_url, "Accessibility.getFullAXTree")
    return ax_tree.get("nodes", [])
```
Each node in `ax_tree` contains:
- `role`: (`button`, `heading`, `link`, `textbox`, `checkbox`, etc.)
- `name`: Accessible text label / title.
- `value`: Current input field value.
- `backendDOMNodeId`: Direct reference to underlying DOM element.

---

### 7.3 Smart DOM Interaction Patterns

#### Pattern A: Reliable Synthetic Clicks
Regular `.click()` can fail on modern web apps listening for pointer events. Use this synthetic trigger:
```javascript
function safeClick(selector) {
  const el = document.querySelector(selector);
  if (!el) return false;
  el.scrollIntoView({ behavior: 'instant', block: 'center' });
  ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'].forEach(evt => {
    el.dispatchEvent(new MouseEvent(evt, { bubbles: true, cancelable: true, view: window }));
  });
  return true;
}
```

#### Pattern B: Arabic & UTF-8 Form Filling
Inject text and immediately trigger standard reactive framework events (`input`, `change`):
```javascript
function fillInput(selector, text) {
  const el = document.querySelector(selector);
  if (!el) return false;
  el.focus();
  el.value = text;
  el.dispatchEvent(new Event('input', { bubbles: true }));
  el.dispatchEvent(new Event('change', { bubbles: true }));
  return true;
}
```

#### Pattern C: Deterministic Wait for Element (No Blind Sleep)
```javascript
function waitForElement(selector, timeoutMs = 8000) {
  return new Promise((resolve, reject) => {
    const el = document.querySelector(selector);
    if (el) return resolve(true);
    const observer = new MutationObserver(() => {
      if (document.querySelector(selector)) {
        observer.disconnect();
        resolve(true);
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
    setTimeout(() => {
      observer.disconnect();
      reject(new Error('Timeout waiting for ' + selector));
    }, timeoutMs);
  });
}
```

#### Pattern D: Overriding Page Visibility & Focus (Silent Headless Bypass)
When a site blocks buttons or countdowns claiming *"Window must be visible / active"*, spoof the Page Visibility API silently via CDP without even opening split-screen:
```javascript
function forcePageVisible() {
  // 1. Override standard visibility properties
  Object.defineProperty(document, 'visibilityState', { value: 'visible', writable: true, configurable: true });
  Object.defineProperty(document, 'hidden', { value: false, writable: true, configurable: true });
  
  // 2. Dispatch events to notify listeners
  document.dispatchEvent(new Event('visibilitychange'));
  window.dispatchEvent(new Event('focus'));
  
  // 3. Spoof document.hasFocus
  document.hasFocus = () => true;
  return true;
}
```
In Python CDP, also enable focus emulation:
```python
await chrome.send_cdp(page_ws, "Emulation.setFocusEmulationEnabled", {"enabled": True})
```

#### Pattern E: Physical Viewability & Quick Bring-to-Front with Auto-Return
When a site uses strict hardware GPU compositing or `IntersectionObserver` where the button must physically be drawn on the display before activating:
1. **Physical Split-Screen (AOSP / Stock Android):**
   ```bash
   adb -s 127.0.0.1:5555 shell am start -n com.android.chrome/com.google.android.apps.chrome.Main --windowingMode 4
   ```
2. **Universal Fast Focus + Auto-Return (Resilient on Samsung One UI & All Devices):**
   Temporarily bring Chrome to front for 0.5s to composite the frame, trigger click, then instantly restore user's active app without losing position:
   ```bash
   # 1. Bring Chrome to front to composite frame
   adb -s 127.0.0.1:5555 shell am start -n com.android.chrome/com.google.android.apps.chrome.Main
   # 2. Trigger synthetic click via CDP
   # 3. Immediately return user to their working app (e.g., Companion or Termux)
   adb -s 127.0.0.1:5555 shell am start -n com.antigravity.companion/com.antigravity.companion.MainActivity
   ```
3. **Scroll Element Directly into Viewport Center & Click:**
   ```javascript
   function scrollAndClick(selector) {
     const el = document.querySelector(selector);
     if (!el) return false;
     // Scroll element into viewport center to satisfy IntersectionObserver
     el.scrollIntoView({ behavior: 'instant', block: 'center', inline: 'center' });
     
     // Dispatch synthetic events
     ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'].forEach(evt => {
       el.dispatchEvent(new MouseEvent(evt, { bubbles: true, cancelable: true, view: window }));
     });
     return true;
   }
   ```

---

## 8. Phase 4: Content Scraping & Clean Extraction

### 8.1 Extracting Article & Readable Text
Extract full page text stripped of script tags, ads, and navigation clutter:
```javascript
function extractCleanContent() {
  const clone = document.body.cloneNode(true);
  const unwanted = clone.querySelectorAll('script, style, noscript, nav, footer, header, svg, aside');
  unwanted.forEach(n => n.remove());
  return {
    title: document.title,
    url: location.href,
    text: clone.innerText.replace(/\n\s*\n/g, '\n').trim()
  };
}
```

### 8.2 Structured Data Extraction (Tables & Lists)
```javascript
function extractTableData(tableSelector) {
  const rows = Array.from(document.querySelectorAll(`${tableSelector} tr`));
  return rows.map(r => Array.from(r.querySelectorAll('th, td')).map(c => c.innerText.trim()));
}
```

### 8.3 Page and Element Screenshots via CDP
Capture a screenshot directly from Chromium rendering buffer without taking a full-device screenshot:

> [!NOTE]
> On Android, Chromium pauses compositor surface frames when a tab is in the background or not rendering. To ensure `Page.captureScreenshot` returns immediately without waiting for a frame:
> 1. Activate the target tab first: call `Target.activateTarget` via the browser WebSocket or `/json/activate/<id>`.
> 2. Wrap the call with a timeout guard (e.g., 3-5 seconds).

```python
import base64
import asyncio

async def capture_page_screenshot(chrome, browser_ws, target_id, page_ws, save_path="/tmp/page.png"):
    # 1. Activate tab to trigger compositor frame
    await chrome.send_cdp(browser_ws, "Target.activateTarget", {"targetId": target_id})
    await asyncio.sleep(0.4)
    # 2. Capture screenshot buffer
    res = await chrome.send_cdp(page_ws, "Page.captureScreenshot", {"format": "png"})
    raw_data = base64.b64decode(res["data"])
    with open(save_path, "wb") as f:
        f.write(raw_data)
```

---

## 9. Phase 5: Network, Cookies & User-Agent Management

### 9.1 Desktop Site Mode Switching
Toggle between mobile and desktop rendering inside any tab:
```python
async def set_desktop_mode(chrome, ws_url, enable=True):
    if enable:
        desktop_ua = (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        await chrome.send_cdp(ws_url, "Emulation.setUserAgentOverride", {"userAgent": desktop_ua})
        await chrome.send_cdp(ws_url, "Emulation.setDeviceMetricsOverride", {
            "width": 1920, "height": 1080, "deviceScaleFactor": 1, "mobile": False
        })
    else:
        await chrome.send_cdp(ws_url, "Emulation.clearDeviceMetricsOverride")
```

### 9.2 Handling JavaScript Dialogs (Alert, Confirm, Prompt)
Prevent unhandled dialogs from locking the page:
```python
async def auto_accept_dialogs(chrome, ws_url):
    await chrome.send_cdp(ws_url, "Page.enable")
    await chrome.send_cdp(ws_url, "Page.handleJavaScriptDialog", {"accept": True})
```

---

## 10. Phase 6: Screen Reader Friendly Operation Rules

1. **Window Focus Isolation:**
   - Automation commands sent through CDP execute silently in the V8 engine and do NOT force the virtual accessibility focus away from Termux or Antigravity Companion.
   - The user can continue listening to their current screen reader task while background tabs load or scrape data.
2. **Audio State Monitoring:**
   - If a web page plays audio (media players, background audio), verify through Android AudioService:
     ```bash
     adb -s 127.0.0.1:5555 shell "dumpsys audio | grep -E 'player piid|state:' | tail -n 5"
     ```
3. **No Unannounced Fullscreen Takeovers:**
   - Never run `am start` without `--windowingMode 4` while the user is actively working in another app. Keep Chrome strictly confined to its allocated split-screen pane. Never use `--windowingMode 5` (pop-up view).

---

## 11. Troubleshooting & Common Pitfalls

| Issue | Root Cause | Solution |
|---|---|---|
| `curl: (7) Failed to connect to 127.0.0.1:9222` | ADB port forward missing or Chrome socket closed | Run `adb forward tcp:9222 localabstract:chrome_devtools_remote`. Ensure Chrome is running in split-screen (`--windowingMode 4`). |
| `adb: more than one device/emulator` | Duplicate entries in `adb devices` (e.g. dynamic IP + loopback 5555) | Run `adb disconnect <DYNAMIC_IP>:<PORT>`. Always target `-s 127.0.0.1:5555`. |
| Chrome stops executing JS in background | Android OEM froze background renderers | Move Chrome to Split-Screen (`--windowingMode 4`) and add to whitelist (`dumpsys deviceidle whitelist +com.android.chrome`). |
| Screen reader focus jumping or trapping | Chrome launched in floating/pop-up window | Switch immediately to Split-Screen (`--windowingMode 4`). Pop-up windows (`--windowingMode 5`) break accessibility exploration. |
| `curl` to `/json/new` returns `Could not create new page` or 500 | Android Chromium restricts HTTP new tab endpoint | Use CDP `Target.createTarget` on the browser WebSocket (`/devtools/browser`) or Android intent `am start -d <URL>`. |
| `Page.captureScreenshot` blocks or times out | Tab in background; GPU compositor paused to save battery | Activate target first via `Target.activateTarget` or use a timeout guard. For screen readers, use ARIA AXTree instead. |
| Arabic text typed as `???` or dropped | Using `adb shell input text` instead of CDP | Always inject via CDP `fillInput()` or `Runtime.evaluate` with UTF-8 strings. |
| Web elements shift under soft keyboard | Soft keyboard opened by input click | Run `adb shell input keyevent 111` (Escape) or dismiss via CDP `document.activeElement.blur()`. |

---

## 12. Verification Checklist

Before reporting completion on any browser automation task:
- [ ] Onboarding/ADB setup verified or completed via permanent port `127.0.0.1:5555`.
- [ ] Chrome launched and kept alive strictly via Split-Screen Mode (`--windowingMode 4` or `am stack move-task`). Pop-up view (`--windowingMode 5`) is NOT used.
- [ ] Port forward `tcp:9222 -> localabstract:chrome_devtools_remote` is active.
- [ ] Tab operations performed via CDP `Target.createTarget` or endpoints (`/json`, `/json/close`).
- [ ] Form filling and clicks handled via synthetic DOM events (zero `input text` corruption).
- [ ] Accessibility tree (`Accessibility.getFullAXTree`) used for semantic inspection without freezing screen readers.
- [ ] Zero unannounced app interruptions or TTS speech stutter.

---

## 13. Autonomous Self-Healing & Adaptive Skill Evolution Protocol (TDD-Driven via `writing-skills`)

> [!IMPORTANT]
> **Strict Adherence to `/writing-skills` Standards:**
> Whenever modifying, repairing, or pruning this file, the agent MUST strictly execute the **`/writing-skills`** protocol:
> 1. **Documentation IS Production Code:** Never edit this file based on assumptions or theoretical guesses.
> 2. **RED-GREEN-REFACTOR Cycle:** A documentation patch is only written after witnessing an explicit failure (RED), verifying a reproducible fix with 100% pass rate in `scratch/` (GREEN), and refactoring `SKILL.md` concisely (REFACTOR).
> 3. **Token Budget & Density Invariant:** Always preserve the skill's compact size and delete superseded/obsolete advice.

Following this standard, whenever this skill encounters a new Android OEM restriction, Chromium breaking change, or unhandled runtime failure, the agent MUST execute this self-healing loop:

```
┌────────────────────────────────────────────────────────┐
│ 1. RED: Anomaly & Failure Capture                      │
│    - Record exact failing command & raw error output   │
│    - Freeze execution before doing blind changes       │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│ 2. GREEN: Forensic RCA & Minimal Working Harness       │
│    - Inspect low-level state (dumpsys, unix sockets)   │
│    - Build scratch test script & verify 100% pass rate │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│ 3. REFACTOR: Atomic Self-Patching of SKILL.md          │
│    - Preserve Accessibility Invariants (Immutable)     │
│    - Append proven symptom + cause + fix to Table 11   │
│    - Update code patterns in Section 7.3 if needed     │
└────────────────────────────────────────────────────────┘
```

### Self-Healing Execution Rules:

1. **Step 1: The RED Gate (Failure Isolation):**
   - NEVER hide, swallow, or retry failed commands blindly.
   - Extract the exact symptom (e.g., `Could not create new page`, `mWindowingMode=fullscreen override`, or `Remote end closed connection`).

2. **Step 2: The GREEN Gate (Forensic RCA & Verification):**
   - Run forensic inspection directly on the device:
     - Check abstract domain sockets: `grep -a devtools /proc/net/unix`
     - Check window manager & task stacks: `am stack list` and `dumpsys activity activities`
     - Check battery & idle state: `dumpsys deviceidle whitelist`
   - Create a minimal test harness in `scratch/test_<issue>.py`.
   - Test alternative sanctioned paths until the verification suite achieves a **100% Pass Rate**.

3. **Step 3: The REFACTOR Gate (Auto-Patching `SKILL.md`):**
   - Once verified, the agent MUST immediately open and update `SKILL.md` using atomic, character-accurate edits (`edit_file`):
     - **Add to Troubleshooting Table (Section 11):** Document the exact `Issue | Root Cause | Solution` triplet.
     - **Add or Refine Interaction Patterns (Section 7.3):** Document any newly discovered CDP pattern (e.g., visibility spoofing, split-stack task movement).
   - **Immutable Invariant Guard:**
     - The agent is STRICTLY PROHIBITED from loosening or deleting Section 3 Assistive Technology Invariants (NO `uiautomator dump` spam, NO floating/pop-up windows `--windowingMode 5`, and ALWAYS preserve UTF-8 Arabic text integrity). All self-updates must strictly honor uninterrupted TalkBack / Jieshuo operation.

---

### 13.1 Lean Maintenance & Device-Adaptive Pruning Policy (سياسة ترشيد الحجم والتشذيب الذاتي)

To prevent the skill from bloating into an unmanageable file that consumes excessive context tokens and memory, the agent MUST enforce this **Lean Pruning Policy**:

1. **Strict Token Budget & Density (< 650 Lines):**
   - The skill document must remain concise, high-density, and actionable.
   - Never paste raw debug logs, conversational explanations, or historical narratives into `SKILL.md`.

2. **Supersession over Endless Accumulation (الاستبدال الحاسم بدلاً من التراكم العشوائي):**
   - When a newly discovered and verified method proves to be superior and universally reliable (e.g., `am stack move-task` replacing inconsistent flags, or `Target.createTarget` replacing `/json/new`), the agent MUST **cleanly replace** the inferior/obsolete instruction rather than piling up contradictory workarounds.

3. **OEM & Environment Specialization Tagging (تخصيص الحلول حسب بصمة الجهاز):**
   - Query device profile when troubleshooting:
     ```bash
     adb -s 127.0.0.1:5555 shell "getprop ro.product.manufacturer && getprop ro.build.version.release"
     ```
   - When adding an OEM-specific workaround, tag it explicitly (e.g., `[Samsung One UI 5+]`, `[Xiaomi HyperOS]`).
   - Prune legacy workarounds for obsolete Android versions (Android 10 and older) to keep the skill laser-focused on modern production runtimes (Android 12–16+).

4. **Troubleshooting Table Garbage Collection:**
   - Section 11 (Troubleshooting) is capped at a maximum of **10 high-value rows**.
   - If a new row is added and the table reaches the cap, merge related symptoms or prune outdated edge cases that are already prevented upstream by Phase 1/2 invariants.
