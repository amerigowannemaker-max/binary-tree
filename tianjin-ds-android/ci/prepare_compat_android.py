#!/usr/bin/env python3
"""Use Android 16 SDK and a non-debuggable, non-minified release variant."""
import re
from pathlib import Path

root = Path(__file__).resolve().parents[1]
gradle = root / 'src-tauri/gen/android/app/build.gradle.kts'
text = gradle.read_text()
text, n1 = re.subn(r'compileSdk\s*=\s*\d+', 'compileSdk = 36', text)
text, n2 = re.subn(r'targetSdk\s*=\s*\d+', 'targetSdk = 36', text)
assert n1 == n2 == 1
marker = 'getByName("release") {'
assert text.count(marker) == 1
text = text.replace(marker, marker + '\n            isDebuggable = false\n            isJniDebuggable = false')
text, count = re.subn(r'optimization\s*\{\s*enable\s*=\s*true\s*\}',
                      'optimization { enable = false }', text)
assert count == 1, 'Review the generated Gradle release template before changing it'
gradle.write_text(text)
manifest = root / 'src-tauri/gen/android/app/src/main/AndroidManifest.xml'
xml = manifest.read_text()
if 'android:testOnly=' in xml:
    xml = re.sub(r'android:testOnly="[^"]*"', 'android:testOnly="false"', xml)
else:
    xml = xml.replace('<application', '<application android:testOnly="false"', 1)
manifest.write_text(xml)
print('Configured compileSdk=36, targetSdk=36, release debuggable=false, testOnly=false')
