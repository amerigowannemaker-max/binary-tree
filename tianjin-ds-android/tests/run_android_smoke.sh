#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 tests/smoke.py --mode android --apk "$APK_PATH" 2>&1 | tee verification/android-tests.log
