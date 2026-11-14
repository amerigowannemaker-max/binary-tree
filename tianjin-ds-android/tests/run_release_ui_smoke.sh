#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
trap 'adb logcat -d -v threadtime > verification/release-logcat.txt 2>/dev/null || true' EXIT
python3 tests/release_ui_smoke.py --apk "$EMULATOR_APK" 2>&1 | tee verification/android-release-ui.log
