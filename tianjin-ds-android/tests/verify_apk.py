#!/usr/bin/env python3
"""Check ELF architecture and Android 16 KiB memory page compatibility."""
import hashlib
import json
import struct
import sys
import zipfile
from pathlib import Path

apk = Path(sys.argv[1])
expected_abi = sys.argv[2]
libraries = []
with apk.open('rb') as raw, zipfile.ZipFile(apk) as z:
    abis = sorted({p.split('/')[1] for p in z.namelist() if p.startswith('lib/') and p.endswith('.so')})
    assert abis == [expected_abi], abis
    for entry in z.infolist():
        if not (entry.filename.startswith('lib/') and entry.filename.endswith('.so')):
            continue
        data = z.read(entry)
        assert data[:6] == b'\x7fELF\x02\x01', entry.filename
        machine = struct.unpack_from('<H', data, 18)[0]
        assert machine == {'arm64-v8a': 183, 'x86_64': 62}[expected_abi], machine
        offset = struct.unpack_from('<Q', data, 32)[0]
        entry_size, count = struct.unpack_from('<HH', data, 54)
        alignment = [p[7] for i in range(count)
                     if (p := struct.unpack_from('<IIQQQQQQ', data, offset + i * entry_size))[0] == 1]
        assert alignment and all(a >= 16384 for a in alignment), (entry.filename, alignment)
        raw.seek(entry.header_offset + 26)
        name_length, extra_length = struct.unpack('<HH', raw.read(4))
        zip_offset = entry.header_offset + 30 + name_length + extra_length
        assert entry.compress_type != zipfile.ZIP_STORED or zip_offset % 16384 == 0, zip_offset
        libraries.append({'name': entry.filename, 'elf_machine': machine, 'load_alignment': alignment,
                          'zip_offset': zip_offset, 'supports_16kb_pages': True})
print(json.dumps({'result': 'PASS', 'apk': apk.name, 'bytes': apk.stat().st_size,
                  'sha256': hashlib.sha256(apk.read_bytes()).hexdigest(), 'abis': abis,
                  'native_libraries': libraries}, indent=2))
