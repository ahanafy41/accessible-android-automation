#!/usr/bin/env bash
# ==============================================================================
# Split-Screen Window Manager Helper (AOSP & Samsung One UI Compatible)
# Moves Chrome to Top Split and Companion/Termux to Bottom Split cleanly.
# ==============================================================================

set -euo pipefail

TARGET_DEV="127.0.0.1:5555"

echo "-> [1/4] Ensuring battery whitelist and activity resizing..."
adb -s "$TARGET_DEV" shell dumpsys deviceidle whitelist +com.android.chrome >/dev/null 2>&1 || true
adb -s "$TARGET_DEV" shell settings put global force_resizable_activities 1 >/dev/null 2>&1 || true

echo "-> [2/4] Ensuring Chrome is awake..."
adb -s "$TARGET_DEV" shell am start -n com.android.chrome/com.google.android.apps.chrome.Main >/dev/null 2>&1 || true
sleep 0.5

echo "-> [3/4] Locating Task IDs..."
CHROME_TASK=$(adb -s "$TARGET_DEV" shell "dumpsys activity recents | grep -B 1 'realActivity=.*com.android.chrome' | grep -oE 'taskId=[0-9]+' | head -n 1 | cut -d= -f2" | tr -d '\r\n')
COMPANION_TASK=$(adb -s "$TARGET_DEV" shell "dumpsys activity recents | grep -B 1 'realActivity=.*com.antigravity.companion' | grep -oE 'taskId=[0-9]+' | head -n 1 | cut -d= -f2" | tr -d '\r\n')

if [ -z "$CHROME_TASK" ]; then
    echo "Error: Could not locate Chrome taskId. Please ensure Chrome is opened."
    exit 1
fi

echo "   • Chrome Task: $CHROME_TASK"
if [ -n "$COMPANION_TASK" ]; then
    echo "   • Companion Task: $COMPANION_TASK"
fi

echo "-> [4/4] Snapping tasks into Split-Screen Stacks (Stack 5: Top, Stack 6: Bottom)..."
adb -s "$TARGET_DEV" shell am stack move-task "$CHROME_TASK" 5 true
if [ -n "$COMPANION_TASK" ]; then
    adb -s "$TARGET_DEV" shell am stack move-task "$COMPANION_TASK" 6 true
fi

echo ""
echo "========================================================"
echo "✓ Split-Screen layout successfully applied!"
echo "  Top Half: Chrome"
echo "  Bottom Half: Working Application"
echo "========================================================"
