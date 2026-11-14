#!/usr/bin/env python3
"""Test the non-debuggable release APK using Android accessibility and ADB."""
import argparse
import json
import re
import subprocess
import time
import traceback
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = 'com.study.dsbasics2027'
REPORT = {'mode':'android-release-api36','checks':[]}

def adb(*args):
    return subprocess.check_output(['adb', *args], text=True, stderr=subprocess.STDOUT)

def dump():
    adb('shell','uiautomator','dump','--compressed','/sdcard/study-window.xml')
    xml = adb('exec-out','cat','/sdcard/study-window.xml')
    return ET.fromstring(xml)

def wait_tree(predicate, timeout=60):
    end = time.monotonic() + timeout
    last = None
    while time.monotonic() < end:
        try:
            last = dump()
            if predicate(last): return last
        except Exception:
            pass
        time.sleep(0.5)
    if last is not None:
        (ROOT/'verification/release-ui-last.xml').write_bytes(ET.tostring(last, encoding='utf-8'))
    raise AssertionError('Android release UI did not reach the expected state')

def texts(tree):
    return '\n'.join(n.get('text','')+' '+n.get('content-desc','') for n in tree.iter('node'))

def edit(tree):
    return next((n for n in tree.iter('node') if n.get('class')=='android.widget.EditText'),None)

def tap_node(node):
    x1,y1,x2,y2 = map(int,re.findall(r'\d+',node.get('bounds','')))
    assert x2>x1 and y2>y1,node.attrib
    adb('shell','input','tap',str((x1+x2)//2),str((y1+y2)//2))

def tap_text(label):
    for _ in range(6):
        tree = dump()
        nodes = [n for n in tree.iter('node') if label in (n.get('text','')+' '+n.get('content-desc','')) and n.get('clickable')=='true'
                 and len(re.findall(r'-?\d+',n.get('bounds','')))==4
                 and (lambda b:b[2]>b[0]>=0 and b[3]>b[1]>=0)(list(map(int,re.findall(r'-?\d+',n.get('bounds','')))))]
        nodes.sort(key=lambda n:n.get('class')!='android.widget.Button')
        if nodes:
            tap_node(nodes[0]);return
        size = re.findall(r'(\d+)x(\d+)',adb('shell','wm','size'))[-1]
        width,height=map(int,size)
        adb('shell','input','swipe',str(width//2),str(height*3//4),str(width//2),str(height//3),'300')
    raise AssertionError('Could not find release UI button: '+label)

def restart():
    adb('shell','am','force-stop',PACKAGE)
    adb('shell','am','start','-W','-n',PACKAGE+'/.MainActivity')
    return wait_tree(lambda t:edit(t) is not None,90)

def passed(name):
    REPORT['checks'].append({'name':name,'result':'PASS'})
    print('PASS:',name,flush=True)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apk',required=True);args=parser.parse_args()
    print(adb('install','-r',args.apk),flush=True)
    adb('shell','pm','clear',PACKAGE)
    tree=restart()
    assert '210' in texts(tree),texts(tree)
    passed('Non-debuggable release installs without adb -t and renders the 210-question page on API 36')
    tap_node(edit(tree))
    adb('shell','input','text','draft_test_123')
    adb('shell','input','keyevent','KEYCODE_ESCAPE')
    wait_tree(lambda t:edit(t) is not None and edit(t).get('text')=='draft_test_123')
    time.sleep(1)
    tree=restart()
    assert edit(tree).get('text')=='draft_test_123',edit(tree).attrib
    passed('Real SQLite automatically saves an unsubmitted draft and restores it after force-stop')
    tap_text('下一题')
    wait_tree(lambda t:'回答有误' in texts(t) and '已放入错题集' in texts(t))
    passed('Wrong input is graded automatically and added to the wrong-question book')
    tree=restart()
    assert '回答有误' in texts(tree) and '已放入错题集' in texts(tree),texts(tree)
    passed('Wrong result and wrong-question membership survive a second force-stop')
    tap_text('记为正确')
    wait_tree(lambda t:'回答正确' in texts(t))
    tree=restart()
    assert '回答正确' in texts(tree),texts(tree)
    assert '已放入错题集' not in texts(tree),texts(tree)
    passed('Manual correction removes the question from the wrong book and persists after restart')
    REPORT['result']='PASS'

if __name__=='__main__':
    (ROOT/'verification').mkdir(exist_ok=True)
    try:main()
    except Exception as error:
        REPORT['result']='FAIL';REPORT['failure']=str(error);traceback.print_exc();raise
    finally:
        (ROOT/'verification/android-release-test-report.json').write_text(json.dumps(REPORT,ensure_ascii=False,indent=2)+'\n')
