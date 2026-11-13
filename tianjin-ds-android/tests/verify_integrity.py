#!/usr/bin/env python3
"""Reject changes to the uploaded question bank or the original page."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / 'src/main.js').read_text()
questions = json.loads(re.search(r'const QUESTIONS = (\[.*?\]);\n', source).group(1))
expected = json.loads((ROOT / 'verification/original-integrity.json').read_text())
actual = {
    'question_count': len(questions),
    'questions_sha256': hashlib.sha256(json.dumps(questions, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest(),
    'index_html_sha256': hashlib.sha256((ROOT / 'index.html').read_bytes()).hexdigest(),
}
assert actual == expected, {'expected': expected, 'actual': actual}
assert [q['id'] for q in questions] == list(range(1, 211))
print(json.dumps({'result': 'PASS', 'integrity': actual}, ensure_ascii=False, indent=2))
