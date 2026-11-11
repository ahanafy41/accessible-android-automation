#!/usr/bin/env bash
# ==============================================================================
# Setup Permanent On-Device ADB (Port 5555 Mode)
# Enables Termux to control Android loopback without active Wi-Fi debugging toggle.
# ==============================================================================

set -euo pipefail

echo "========================================================"
echo " Accessible Android Automation - ADB Setup Helper"
echo "========================================================"

if [ "$#" -lt 1 ]; then
    echo "Usage: bash $0 <DYNAMIC_IP:PORT> [PAIRING_CODE]"
    echo ""
    echo "Example:"
    echo "  1) First-time pairing:"
    echo "     bash $0 192.168.1.5:37563 829143"
    echo "  2) Connect & promote to permanent 5555:"
    echo "     bash $0 192.168.1.5:43309"
    exit 1
fi

TARGET="$1"
PAIRING_CODE="${2:-}"

if [ -n "$PAIRING_CODE" ]; then
    echo "-> [1/4] Pairing with $TARGET using code $PAIRING_CODE..."
    adb pair "$TARGET" "$PAIRING_CODE"
fi

echo "-> [2/4] Connecting to dynamic port $TARGET..."
adb connect "$TARGET"

echo "-> [3/4] Promoting adbd daemon to permanent port 5555..."
adb -s "$TARGET" tcpip 5555
sleep 1

echo "-> [4/4] Connecting to local permanent loopback (127.0.0.1:5555)..."
adb connect 127.0.0.1:5555

echo "-> Cleaning up dynamic session to prevent duplicate devices..."
adb disconnect "$TARGET" || true

echo ""
echo "========================================================"
echo "✓ Success! Device is now connected permanently via loopback:"
adb devices
echo "========================================================"
