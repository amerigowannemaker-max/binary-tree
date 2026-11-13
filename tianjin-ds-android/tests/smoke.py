#!/usr/bin/env python3
"""Exercise the shipped UI with SQLite; Android mode uses the real Tauri plugin.

Browser mode replaces ONLY the native IPC transport, with a real SQLite database.
Android mode connects to the debug WebView over ADB and does not mock the plugin.
"""
import argparse
import functools
import json
import re
import sqlite3
import subprocess
import tempfile
import threading
import time
import traceback
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = 'com.study.dsbasics2027'
SOURCE = (ROOT / 'src/main.js').read_text()
QUESTIONS = json.loads(re.search(r'const QUESTIONS = (\[.*?\]);\n', SOURCE).group(1))
REPORT = {'mode': None, 'checks': [], 'errors': []}


def passed(name, **details):
    REPORT['checks'].append({'name': name, 'result': 'PASS', **details})
    print('PASS:', name, flush=True)


def adb(*args):
    return subprocess.check_output(['adb', *args], text=True, stderr=subprocess.STDOUT)


class SQLiteHandler(SimpleHTTPRequestHandler):
    db_path = None

    def log_message(self, *_):
        pass

    def do_POST(self):
        try:
            body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            command, args = body['command'], body['args']
            if command == 'plugin:sql|load':
                result = args['db']
            else:
                with sqlite3.connect(self.db_path, timeout=20) as con:
                    con.row_factory = sqlite3.Row
                    cursor = con.execute(args['query'], args.get('values', []))
                    result = ([dict(row) for row in cursor.fetchall()] if command.endswith('|select')
                              else [max(cursor.rowcount, 0), cursor.lastrowid])
            payload = json.dumps({'result': result}, ensure_ascii=False).encode()
            self.send_response(200)
        except Exception as error:
            payload = json.dumps({'error': str(error)}).encode()
            self.send_response(500)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(payload)


BRIDGE = """window.__TAURI_INTERNALS__ = {invoke: async (command, args) => {
 const response = await fetch('/__sqlite_test_bridge', {method:'POST',
 headers:{'Content-Type':'application/json'},body:JSON.stringify({command,args})});
 const data = await response.json(); if (!response.ok) throw Error(data.error);
 return data.result;
}};"""


def select(page, query):
    return page.evaluate("""async query => window.__TAURI_INTERNALS__.invoke(
      'plugin:sql|select', {db:'sqlite:study.db',query,values:[]})""", query)


def saved(page):
    rows = select(page, 'SELECT json_state FROM app_state WHERE id = 1')
    return json.loads(rows[0]['json_state']) if rows else {}


def wait_saved(page, predicate):
    end = time.monotonic() + 30
    while time.monotonic() < end:
        value = saved(page)
        if predicate(value):
            return value
        time.sleep(0.1)
    raise AssertionError('SQLite state did not reach expected value: ' + json.dumps(saved(page), ensure_ascii=False))


def question(page, number):
    expect(page.locator('.modehint').filter(has_text=f'题库 #{number}）')).to_have_count(1)


def scenarios(page, reopen, exhaustive):
    expect(page.locator('#answerInput')).to_be_visible(timeout=60000)
    expect(page.locator('#totalTag')).to_have_text('210 题')
    assert list(select(page, 'PRAGMA integrity_check')[0].values()) == ['ok']
    passed('SQLite opens and passes integrity_check; all 210 questions are present')

    page.locator('#answerInput').fill('首次启动清空回归测试')
    wait_saved(page, lambda s: bool(s.get('records')))
    page.locator('summary').click()
    page.once('dialog', lambda dialog: dialog.accept())
    page.locator('#resetAllBtn').click()
    wait_saved(page, lambda s: s.get('records') == {})
    page.locator('summary').click()
    passed('Clear-all on first launch does not reuse mutated default records')

    draft = "草稿 O'Reilly; DROP TABLE app_state; 😀"
    page.locator('#answerInput').fill(draft)
    wait_saved(page, lambda s: s.get('records', {}).get('1', {}).get('text') == draft)
    page = reopen()
    expect(page.locator('#answerInput')).to_have_value(draft)
    passed('Unsubmitted Unicode draft auto-saves with bound SQL parameters and survives restart')

    page.locator('#answerInput').fill('测试错误答案')
    page.locator('#nextBtn').click()
    question(page, 1)
    expect(page.locator('.restitle')).to_have_text('✗ 回答有误')
    wait_saved(page, lambda s: s['records']['1'].get('status') == 'wrong' and s['records']['1'].get('wrongbook'))
    page = reopen()
    expect(page.locator('#wrongBookBtn')).to_have_attribute('aria-pressed', 'true')
    expect(page.locator('#wrong')).to_have_text('1')
    passed('Wrong answer stays on the current question and persists in the wrong-question book')

    page.locator('[data-mode="wrong"]').click()
    question(page, 1)
    page.locator('#answerInput').fill('运算')
    page.locator('#nextBtn').click()
    expect(page.locator('#wrong')).to_have_text('0')
    wait_saved(page, lambda s: s['records']['1'].get('status') == 'right' and not s['records']['1'].get('wrongbook'))
    passed('Correcting a wrong answer removes it from the wrong-question book')

    page.locator('[data-mode="all"]').click()
    page.locator('#nextBtn').click()
    question(page, 2)
    page.locator('#answerInput').fill('逻辑')
    page.locator('#answerInput').press('Enter')
    question(page, 3)
    passed('Correct answer advances; Enter grades and advances')

    page.locator('#wrongBookBtn').click()
    page.locator('#starBtn').click()
    wait_saved(page, lambda s: s['records']['3'].get('wrongbook') and s['records']['3'].get('star'))
    page = reopen()
    question(page, 3)
    expect(page.locator('#wrongBookBtn')).to_have_attribute('aria-pressed', 'true')
    expect(page.locator('#starBtn')).to_have_class('star on')
    page.locator('#wrongBookBtn').click()
    expect(page.locator('#wrong')).to_have_text('0')
    passed('Manual wrong-book membership, favorites, and current position survive restart')

    page.locator('#answerInput').fill('存储')
    page.locator('#answerInput').evaluate("el => el.dispatchEvent(new KeyboardEvent('keydown', {key:'Enter',isComposing:true,bubbles:true}))")
    question(page, 3)
    assert saved(page)['records']['3'].get('status') is None
    passed('Android IME composition Enter does not submit the answer')

    page.locator('#answerInput').evaluate("""el => {for (let i=0;i<60;i++) {
      el.value='快速输入'+i;el.dispatchEvent(new Event('input',{bubbles:true}));}
      el.value='存储';el.dispatchEvent(new Event('input',{bubbles:true}));} """)
    wait_saved(page, lambda s: s['records']['3'].get('text') == '存储')
    page.locator('#nextBtn').click()
    question(page, 4)
    wait_saved(page, lambda s: s.get('current') == 4 and s['records']['3'].get('status') == 'right')
    page = reopen()
    question(page, 4)
    passed('Rapid inputs keep the newest snapshot; grading and position restore after restart')

    # This catches the original shallow-copy aliasing of DEFAULT.records.
    page.locator('summary').click()
    page.once('dialog', lambda dialog: dialog.accept())
    page.locator('#resetAllBtn').click()
    wait_saved(page, lambda s: s.get('records') == {} and s.get('current') == 1)
    page = reopen()
    expect(page.locator('#done')).to_have_text('0')
    expect(page.locator('#wrong')).to_have_text('0')
    expect(page.locator('#answerInput')).to_have_value('')
    passed('Clear-all actually clears records and stays cleared after restart')

    if exhaustive:
        for q in QUESTIONS:
            question(page, q['id'])
            page.locator('#answerInput').fill(q['a'])
            page.locator('#nextBtn').click()
        wait_saved(page, lambda s: len(s.get('records', {})) == 210 and all(r.get('status') == 'right' for r in s['records'].values()))
        expect(page.locator('#done')).to_have_text('210')
        expect(page.locator('#right')).to_have_text('210')
        expect(page.locator('#wrong')).to_have_text('0')
        passed('All 210 original standard answers grade correctly in the shipped production UI')
        functions = '\n'.join(re.search(r'function '+name+r'\([^\n]+', SOURCE).group() for name in ['normalize', 'equivalent'])
        result = page.evaluate('(questions) => {' + functions + '\n return questions.flatMap(q => [q.a,...q.alt].filter(a=>!equivalent(a,q)).map(a=>({id:q.id,answer:a})));}', QUESTIONS)
        assert result == [], result
        passed('All original accepted alternative answers pass normalization', answer_forms=sum(1 + len(q['alt']) for q in QUESTIONS))
    REPORT['final_state'] = saved(page)
    return page


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['browser', 'android'], default='browser')
    parser.add_argument('--chromium')
    parser.add_argument('--apk')
    args = parser.parse_args()
    REPORT['mode'] = args.mode
    ROOT.joinpath('verification').mkdir(exist_ok=True)
    with sync_playwright() as pw:
        if args.mode == 'browser':
            with tempfile.TemporaryDirectory() as temp:
                SQLiteHandler.db_path = str(Path(temp) / 'study.db')
                server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(SQLiteHandler, directory=str(ROOT / 'dist')))
                threading.Thread(target=server.serve_forever, daemon=True).start()
                options = {'headless': True, 'args': ['--no-sandbox']}
                if args.chromium:
                    options['executable_path'] = args.chromium
                browser = pw.chromium.launch(**options)
                context = browser.new_context(viewport={'width': 412, 'height': 915})
                context.add_init_script(BRIDGE)
                page = context.new_page()
                page.on('pageerror', lambda e: REPORT['errors'].append(str(e)))
                url = f'http://127.0.0.1:{server.server_port}/'
                page.goto(url)

                def reopen():
                    page.reload()
                    expect(page.locator('#answerInput')).to_be_visible(timeout=30000)
                    return page

                page = scenarios(page, reopen, exhaustive=True)
                browser.close()
                server.shutdown()
        else:
            assert args.apk, '--apk is required for Android mode'
            adb('install', '-r', args.apk)
            adb('shell', 'pm', 'clear', PACKAGE)
            browsers = []

            def reopen():
                adb('shell', 'am', 'force-stop', PACKAGE)
                adb('shell', 'monkey', '-p', PACKAGE, '-c', 'android.intent.category.LAUNCHER', '1')
                deadline = time.monotonic() + 90
                error = None
                while time.monotonic() < deadline:
                    try:
                        sockets = re.findall(r'@(webview_devtools_remote[^\s]*)', adb('shell', 'cat', '/proc/net/unix'))
                        for socket in sockets:
                            adb('forward', 'tcp:9222', 'localabstract:' + socket)
                            browser = pw.chromium.connect_over_cdp('http://127.0.0.1:9222', timeout=5000)
                            browsers.append(browser)
                            page = browser.contexts[0].pages[0]
                            page.on('pageerror', lambda e: REPORT['errors'].append(str(e)))
                            expect(page.locator('#answerInput')).to_be_visible(timeout=20000)
                            return page
                    except Exception as exc:
                        error = exc
                    time.sleep(1)
                raise RuntimeError('Could not attach to Android WebView: ' + str(error))

            page = scenarios(reopen(), reopen, exhaustive=False)
            # Verify the database is an on-device file in this app's sandbox.
            files = adb('shell', 'run-as', PACKAGE, 'find', '.', '-name', 'study.db')
            assert 'study.db' in files, files
            passed('Native SQLite database exists inside the Android application sandbox', database=files.strip())
            adb('logcat', '-d', '-v', 'threadtime', '-f', '/data/local/tmp/ds-logcat.txt')
            subprocess.run(['adb', 'pull', '/data/local/tmp/ds-logcat.txt', str(ROOT / 'verification/android-logcat.txt')], check=True)
    assert not REPORT['errors'], REPORT['errors']
    REPORT['result'] = 'PASS'


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        REPORT['result'] = 'FAIL'
        REPORT['failure'] = str(error)
        traceback.print_exc()
        raise
    finally:
        ROOT.joinpath('verification').mkdir(exist_ok=True)
        (ROOT / f'verification/{REPORT["mode"] or "unknown"}-test-report.json').write_text(json.dumps(REPORT, ensure_ascii=False, indent=2) + '\n')
