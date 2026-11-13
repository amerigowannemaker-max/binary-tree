#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
trap 'adb logcat -d -v threadtime > verification/android-logcat.txt 2>/dev/null || true' EXIT
python3 tests/smoke.py --mode android --apk "$APK_PATH" 2>&1 | tee verification/android-tests.log
