# -*- coding: utf-8 -*-
"""校验 .docx 包结构：必备部件是否齐全、每个 XML 是否合法、正文段落与表格数量。"""
import sys
import zipfile
import xml.etree.ElementTree as ET

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
REQUIRED = [
    '[Content_Types].xml',
    '_rels/.rels',
    'word/document.xml',
    'word/_rels/document.xml.rels',
    'word/styles.xml',
]

ok = True
for path in sys.argv[1:]:
    print('=' * 70)
    print('检查文件：', path)
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        bad = z.testzip()
        print('  ZIP 完整性 :', '正常' if bad is None else '损坏 -> %s' % bad)
        for req in REQUIRED:
            exist = req in names
            if not exist:
                ok = False
            print('  必备部件   : %-32s %s' % (req, '有' if exist else '缺失！'))
        for name in names:
            if name.endswith('.xml') or name.endswith('.rels'):
                try:
                    ET.fromstring(z.read(name))
                except Exception as exc:
                    ok = False
                    print('  XML 解析失败: %s -> %s' % (name, exc))
        doc = ET.fromstring(z.read('word/document.xml'))
        body = doc.find(W + 'body')
        paras = len(body.findall(W + 'p'))
        tables = len(body.findall(W + 'tbl'))
        text_len = sum(len(t.text or '') for t in doc.iter(W + 't'))
        print('  正文段落数 :', paras)
        print('  表格数量   :', tables)
        print('  纯文字总量 :', text_len, '字符')
        if paras == 0:
            ok = False
            print('  ！正文为空')

print('=' * 70)
print('校验结果：', '全部通过' if ok else '存在问题')
sys.exit(0 if ok else 1)
