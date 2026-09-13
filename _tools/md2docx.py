# -*- coding: utf-8 -*-
"""
极简 Markdown → .docx 生成器（只用标准库，不依赖 python-docx / Word）
支持的语法：
  # ~ ####     标题（对应 Word 的“标题 1~4”样式，可用于自动生成目录）
  - xxx        无序列表
  1. xxx       有序列表
  > xxx        引用 / 提示框
  ```lang ... ``` 代码块（等宽字体 + 灰色底纹 + 边框）
  | a | b |    表格（第二行必须是 |---|---| 分隔行）
  ---          分隔线
  [[TOC]]      插入 Word 目录域（打开后右键“更新域”即可生成目录）
  正文里可用 **加粗** 和 `行内代码`
"""
import re
import sys
import zipfile

W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def esc(text):
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


def run(text, bold=False, code=False, color=None, size=None, italic=False):
    rpr = '<w:rPr>'
    if code:
        rpr += '<w:rFonts w:ascii="Consolas" w:hAnsi="Consolas" w:eastAsia="宋体" w:cs="Consolas"/>'
    if bold:
        rpr += '<w:b/><w:bCs/>'
    if italic:
        rpr += '<w:i/>'
    if color:
        rpr += '<w:color w:val="%s"/>' % color
    if code:
        rpr += '<w:shd w:val="clear" w:color="auto" w:fill="EFEFEF"/>'
    if size:
        rpr += '<w:sz w:val="%d"/><w:szCs w:val="%d"/>' % (size, size)
    rpr += '</w:rPr>'
    return '<w:r>%s<w:t xml:space="preserve">%s</w:t></w:r>' % (rpr, esc(text))


INLINE = re.compile(r'(\*\*.+?\*\*|`[^`]+`)')


def inline_runs(text, base_bold=False, color=None, size=None):
    out = []
    for part in INLINE.split(text):
        if not part:
            continue
        if part.startswith('**') and part.endswith('**') and len(part) > 4:
            out.append(run(part[2:-2], bold=True, color=color, size=size))
        elif part.startswith('`') and part.endswith('`') and len(part) > 2:
            out.append(run(part[1:-1], code=True, color=color, size=size))
        else:
            out.append(run(part, bold=base_bold, color=color, size=size))
    return ''.join(out)


def para(runs_xml, style=None, align=None, indent=None, hanging=None, spacing=None, shade=None,
         border_bottom=None, keep_next=False):
    ppr = '<w:pPr>'
    if style:
        ppr += '<w:pStyle w:val="%s"/>' % style
    if keep_next:
        ppr += '<w:keepNext/>'
    if border_bottom:
        ppr += ('<w:pBdr><w:bottom w:val="single" w:sz="12" w:space="4" w:color="%s"/></w:pBdr>'
                % border_bottom)
    if shade:
        ppr += '<w:shd w:val="clear" w:color="auto" w:fill="%s"/>' % shade
    if spacing:
        ppr += '<w:spacing %s/>' % spacing
    if indent is not None:
        ppr += '<w:ind w:left="%d"%s/>' % (indent, (' w:hanging="%d"' % hanging) if hanging else '')
    if align:
        ppr += '<w:jc w:val="%s"/>' % align
    ppr += '</w:pPr>'
    return '<w:p>%s%s</w:p>' % (ppr, runs_xml)


def code_block(lines):
    """代码块：外面套一个单元格表格，形成灰底 + 边框的“代码框”"""
    rows = []
    for line in lines:
        line = line.replace('\t', '    ')
        size = 19 if len(line) <= 78 else (17 if len(line) <= 92 else 15)
        rows.append('<w:p><w:pPr><w:pStyle w:val="Code"/><w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/></w:pPr>'
                    + run(line if line else ' ', size=size) + '</w:p>')
    cell = ('<w:tc><w:tcPr><w:tcW w:w="9600" w:type="dxa"/>'
            '<w:shd w:val="clear" w:color="auto" w:fill="F7F7F7"/>'
            '<w:tcMar><w:top w:w="120" w:type="dxa"/><w:bottom w:w="120" w:type="dxa"/>'
            '<w:left w:w="160" w:type="dxa"/><w:right w:w="120" w:type="dxa"/></w:tcMar>'
            '</w:tcPr>%s</w:tc>' % ''.join(rows))
    borders = ('<w:tblBorders>'
               '<w:top w:val="single" w:sz="6" w:color="D9D9D9"/>'
               '<w:left w:val="single" w:sz="6" w:color="D9D9D9"/>'
               '<w:bottom w:val="single" w:sz="6" w:color="D9D9D9"/>'
               '<w:right w:val="single" w:sz="6" w:color="D9D9D9"/>'
               '<w:insideH w:val="none" w:sz="0" w:color="auto"/>'
               '<w:insideV w:val="none" w:sz="0" w:color="auto"/>'
               '</w:tblBorders>')
    tbl = ('<w:tbl><w:tblPr><w:tblW w:w="9600" w:type="dxa"/>%s'
           '<w:tblCellMar><w:top w:w="60" w:type="dxa"/><w:bottom w:w="60" w:type="dxa"/></w:tblCellMar>'
           '</w:tblPr><w:tblGrid><w:gridCol w:w="9600"/></w:tblGrid>'
           '<w:tr>%s</w:tr></w:tbl>' % (borders, cell))
    return tbl + '<w:p><w:pPr><w:spacing w:after="0" w:line="200" w:lineRule="auto"/></w:pPr></w:p>'


def table(headers, rows):
    def cell(text, header=False, widths=None, idx=0):
        shd = 'DCE6F1' if header else 'FFFFFF'
        rpr_bold = header
        width = widths[idx] if widths else int(9000 / max(1, len(headers)))
        return ('<w:tc><w:tcPr><w:tcW w:w="%d" w:type="dxa"/><w:shd w:val="clear" w:color="auto" w:fill="%s"/>'
                '<w:vAlign w:val="center"/></w:tcPr>%s</w:tc>'
                % (width, shd, para(inline_runs(text, base_bold=rpr_bold, size=19),
                                    spacing='w:before="40" w:after="40" w:line="240" w:lineRule="auto"')))

    ncol = len(headers)
    widths = [int(9600 / ncol)] * ncol
    widths[-1] = 9600 - sum(widths[:-1])

    out = ['<w:tbl><w:tblPr><w:tblW w:w="9600" w:type="dxa"/>',
           '<w:tblBorders>',
           '<w:top w:val="single" w:sz="6" w:color="BFBFBF"/>',
           '<w:left w:val="single" w:sz="6" w:color="BFBFBF"/>',
           '<w:bottom w:val="single" w:sz="6" w:color="BFBFBF"/>',
           '<w:right w:val="single" w:sz="6" w:color="BFBFBF"/>',
           '<w:insideH w:val="single" w:sz="6" w:color="BFBFBF"/>',
           '<w:insideV w:val="single" w:sz="6" w:color="BFBFBF"/>',
           '</w:tblBorders><w:tblLayout w:type="fixed"/></w:tblPr><w:tblGrid>']
    out += ['<w:gridCol w:w="%d"/>' % w for w in widths]
    out.append('</w:tblGrid>')
    out.append('<w:tr><w:trPr><w:tblHeader/></w:trPr>'
               + ''.join(cell(h, True, widths, i) for i, h in enumerate(headers)) + '</w:tr>')
    for row in rows:
        cells = list(row) + [''] * (ncol - len(row))
        out.append('<w:tr>' + ''.join(cell(c, False, widths, i) for i, c in enumerate(cells[:ncol])) + '</w:tr>')
    out.append('</w:tbl>')
    out.append('<w:p><w:pPr><w:spacing w:after="0" w:line="200" w:lineRule="auto"/></w:pPr></w:p>')
    return ''.join(out)


def toc_field():
    return ('<w:p><w:pPr><w:pStyle w:val="TOC1"/><w:spacing w:before="120" w:after="120"/></w:pPr>'
            '<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
            '<w:r><w:instrText xml:space="preserve"> TOC \\o "1-3" \\h \\z \\u </w:instrText></w:r>'
            '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
            + run('【目录：在 Word 中右键此处 → 更新域 → 更新整个目录】') +
            '<w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>')


def split_row(line):
    """按 | 切分表格行，支持用 \\| 转义单元格内的竖线（如 Markdown 里的 || 运算符）"""
    line = line.strip()
    if line.startswith('|'):
        line = line[1:]
    if line.endswith('|'):
        line = line[:-1]
    parts = re.split(r'(?<!\\)\|', line)
    return [p.replace('\\|', '|').strip() for p in parts]


def render(md):
    lines = md.replace('\r\n', '\n').split('\n')
    out = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]

        # 代码块
        if line.strip().startswith('```'):
            i += 1
            buf = []
            while i < n and not lines[i].strip().startswith('```'):
                buf.append(lines[i])
                i += 1
            i += 1
            out.append(code_block(buf))
            continue

        # 表格
        if line.strip().startswith('|') and i + 1 < n and re.match(r'^\s*\|[\s:|-]+\|\s*$', lines[i + 1]):
            headers = split_row(line)
            i += 2
            rows = []
            while i < n and lines[i].strip().startswith('|'):
                rows.append(split_row(lines[i]))
                i += 1
            out.append(table(headers, rows))
            continue

        stripped = line.strip()

        if stripped == '[[TOC]]':
            out.append(toc_field())
            i += 1
            continue

        if stripped == '---':
            out.append('<w:p><w:pPr><w:pBdr><w:bottom w:val="single" w:sz="8" w:space="1" w:color="D0D0D0"/></w:pBdr>'
                       '<w:spacing w:before="120" w:after="120"/></w:pPr></w:p>')
            i += 1
            continue

        if not stripped:
            i += 1
            continue

        m = re.match(r'^(#{1,4})\s+(.*)$', stripped)
        if m:
            level = len(m.group(1))
            out.append(para(inline_runs(m.group(2)), style='Heading%d' % level, keep_next=True))
            i += 1
            continue

        if stripped.startswith('> '):
            out.append(para(inline_runs(stripped[2:]), style='Quote'))
            i += 1
            continue

        m = re.match(r'^[-*]\s+(.*)$', stripped)
        if m:
            out.append(para(run('•  ', bold=True, color='E8452F') + inline_runs(m.group(1)),
                            indent=360, hanging=240, spacing='w:before="20" w:after="20" w:line="288" w:lineRule="auto"'))
            i += 1
            continue

        m = re.match(r'^(\d+)[.、)]\s+(.*)$', stripped)
        if m:
            out.append(para(run(m.group(1) + '. ', bold=True) + inline_runs(m.group(2)),
                            indent=360, hanging=240, spacing='w:before="20" w:after="20" w:line="288" w:lineRule="auto"'))
            i += 1
            continue

        out.append(para(inline_runs(stripped)))
        i += 1
    return ''.join(out)


CONTENT_TYPES = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>'''

RELS = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>'''

DOC_RELS = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>'''


def heading_style(sid, name, size, color, before, after, outline, bold=True, border=None):
    ppr = '<w:pPr><w:keepNext/><w:outlineLvl w:val="%d"/>' % outline
    if border:
        ppr += '<w:pBdr><w:bottom w:val="single" w:sz="12" w:space="4" w:color="%s"/></w:pBdr>' % border
    ppr += '<w:spacing w:before="%d" w:after="%d"/>' % (before, after)
    if sid == 'Heading1':
        ppr += '<w:jc w:val="left"/>'
    ppr += '</w:pPr>'
    return ('<w:style w:type="paragraph" w:styleId="%s"><w:name w:val="%s"/><w:basedOn w:val="Normal"/>'
            '<w:next w:val="Normal"/><w:qFormat/>%s'
            '<w:rPr><w:rFonts w:ascii="Segoe UI" w:hAnsi="Segoe UI" w:eastAsia="微软雅黑"/>'
            '%s<w:color w:val="%s"/><w:sz w:val="%d"/><w:szCs w:val="%d"/></w:rPr></w:style>'
            % (sid, name, ppr, '<w:b/>' if bold else '', color, size, size))


STYLES = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles ''' + W + '''>
<w:docDefaults>
 <w:rPrDefault><w:rPr>
  <w:rFonts w:ascii="Segoe UI" w:hAnsi="Segoe UI" w:eastAsia="微软雅黑" w:cs="Segoe UI"/>
  <w:sz w:val="21"/><w:szCs w:val="21"/>
 </w:rPr></w:rPrDefault>
 <w:pPrDefault><w:pPr><w:spacing w:after="120" w:line="300" w:lineRule="auto"/></w:pPr></w:pPrDefault>
</w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/></w:style>
''' + heading_style('Heading1', 'heading 1', 34, 'B03A22', 360, 180, 0, True, 'E8452F') \
    + heading_style('Heading2', 'heading 2', 28, 'C0561F', 280, 140, 1) \
    + heading_style('Heading3', 'heading 3', 24, '35322E', 220, 100, 2) \
    + heading_style('Heading4', 'heading 4', 22, '6B645C', 180, 80, 3) \
    + '''
<w:style w:type="paragraph" w:styleId="Code"><w:name w:val="Code"/><w:basedOn w:val="Normal"/>
 <w:pPr><w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/></w:pPr>
 <w:rPr><w:rFonts w:ascii="Consolas" w:hAnsi="Consolas" w:eastAsia="宋体"/><w:sz w:val="19"/><w:szCs w:val="19"/></w:rPr>
</w:style>
<w:style w:type="paragraph" w:styleId="Quote"><w:name w:val="Quote"/><w:basedOn w:val="Normal"/>
 <w:pPr><w:pBdr><w:left w:val="single" w:sz="18" w:space="6" w:color="E8452F"/></w:pBdr>
 <w:shd w:val="clear" w:color="auto" w:fill="FDF3F0"/>
 <w:ind w:left="200"/><w:spacing w:before="80" w:after="120"/></w:pPr>
 <w:rPr><w:color w:val="8A4B34"/></w:rPr>
</w:style>
<w:style w:type="paragraph" w:styleId="TOC1"><w:name w:val="toc 1"/><w:basedOn w:val="Normal"/>
 <w:pPr><w:spacing w:after="60"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/>
 <w:pPr><w:spacing w:before="0" w:after="240"/><w:jc w:val="center"/></w:pPr>
 <w:rPr><w:b/><w:color w:val="B03A22"/><w:sz w:val="44"/><w:szCs w:val="44"/></w:rPr></w:style>
</w:styles>'''

SECTPR = ('<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
          '<w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134" w:header="851" w:footer="992" w:gutter="0"/>'
          '</w:sectPr>')

DOC_HEAD = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<w:document ' + W + '><w:body>')


def build(md_path, out_path, title, author='2048 小游戏项目组'):
    with open(md_path, 'r', encoding='utf-8') as f:
        md = f.read()
    body = render(md)
    document = DOC_HEAD + body + SECTPR + '</w:body></w:document>'

    core = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            '<dc:title>%s</dc:title><dc:creator>%s</dc:creator><cp:lastModifiedBy>%s</cp:lastModifiedBy>'
            '</cp:coreProperties>' % (esc(title), esc(author), esc(author)))

    app = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
           'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
           '<Application>Microsoft Office Word</Application></Properties>')

    with zipfile.ZipFile(out_path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', CONTENT_TYPES)
        z.writestr('_rels/.rels', RELS)
        z.writestr('word/document.xml', document)
        z.writestr('word/_rels/document.xml.rels', DOC_RELS)
        z.writestr('word/styles.xml', STYLES)
        z.writestr('docProps/core.xml', core)
        z.writestr('docProps/app.xml', app)
    return out_path


if __name__ == '__main__':
    src, dst, title = sys.argv[1], sys.argv[2], sys.argv[3]
    build(src, dst, title)
    print('生成成功:', dst)
