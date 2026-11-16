# -*- coding: utf-8 -*-
"""
Book Builder server - lets you add / delete content blocks in the book through a simple form.
Run:  python server.py      then open  http://127.0.0.1:8765
The book page auto-paginates in the browser, so inserted blocks flow to the right page by themselves.
"""
import json, os, re, shutil, sys, time, html as htmllib
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, unquote, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
BOOK = os.path.join(KIT, 'from_zero_to_hero_book.html')
BACKUPS = os.path.join(HERE, 'backups')
PORT = 8765
NL = '\r\n'

# ----------------------------------------------------------------------------
# 1. Parse the book source: lessons -> explanation pages -> top-level blocks
# ----------------------------------------------------------------------------
VOID = {'br', 'img', 'hr', 'input', 'meta', 'link', 'area', 'base', 'col', 'embed', 'source', 'track', 'wbr'}


class Mapper(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=False)
        self.text = text
        self.starts = [0] + [m.end() for m in re.finditer('\n', text)]
        self.stack = []
        self.root = {'tag': 'ROOT', 'cls': '', 'children': [], 'start': 0, 'end': len(text)}
        self.stack.append(self.root)

    def off(self):
        line, col = self.getpos()
        return self.starts[line - 1] + col

    def handle_starttag(self, tag, attrs):
        if tag in VOID:
            return
        cls = dict(attrs).get('class', '') or ''
        self.stack.append({'tag': tag, 'cls': cls, 'children': [], 'start': self.off(), 'end': None})

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        for k in range(len(self.stack) - 1, 0, -1):
            if self.stack[k]['tag'] == tag:
                o = self.off()
                end = self.text.index('>', o) + 1
                while len(self.stack) > k:
                    fr = self.stack.pop()
                    fr['end'] = end
                    self.stack[-1]['children'].append(fr)
                return


def strip_tags(s):
    s = re.sub(r'<[^>]+>', ' ', s)
    s = htmllib.unescape(s)
    return re.sub(r'\s+', ' ', s).strip()


TYPE_MAP = [
    ('note-lightbulb-box', 'ملاحظة (Notes)'),
    ('comparison-section', 'جدول'),
    ('sec-heading', 'عنوان قسم'),
    ('lead-paragraph-ar', 'فقرة (عربي)'),
    ('lead-paragraph', 'فقرة'),
    ('lesson-title', 'عنوان الدرس'),
    ('egy-reflection-box', 'مخطط / ميكانيزم'),
    ('real-world-example-box', 'مثال من الواقع'),
    ('concept-card', 'كارت مفهوم'),
    ('breakdown-grid-2', 'كارتين (مشكلة/نتيجة)'),
    ('rules-box', 'قوانين'),
    ('problems-box', 'مسائل محلولة'),
    ('arrow-process-diagram', 'مخطط'),
    ('styled-table', 'جدول'),
]


def block_type(cls):
    toks = cls.split()
    for key, label in TYPE_MAP:
        if key in toks:
            return label
    return 'عنصر'


def parse_book(text):
    m = Mapper(text)
    m.feed(text)
    m.close()
    pages = []

    def walk(node):
        toks = node['cls'].split()
        if 'magazine-spread' in toks:
            for ch in node['children']:
                ctoks = ch['cls'].split()
                if 'page' in ctoks or 'lesson-cover-page' in ctoks:
                    pages.append(ch)
        for ch in node['children']:
            walk(ch)

    walk(m.root)
    info = []
    for pg in pages:
        toks = pg['cls'].split()
        hdr = ftr = None
        blocks = []
        for ch in pg['children']:
            ct = ch['cls'].split()
            if 'page-header' in ct:
                hdr = ch
            elif 'page-footer' in ct:
                ftr = ch
            else:
                blocks.append(ch)
        badge = ''
        lesson_label = ''
        if hdr:
            spans = [c for c in hdr['children'] if c['tag'] == 'span']
            if spans:
                lesson_label = strip_tags(text[spans[0]['start']:spans[0]['end']])
            for c in hdr['children']:
                if 'badge-unit' in c['cls'].split():
                    badge = strip_tags(text[c['start']:c['end']])
        info.append({'node': pg, 'cls': pg['cls'], 'toks': toks, 'hdr': hdr, 'ftr': ftr, 'blocks': blocks,
                     'badge': badge, 'lesson_label': lesson_label})

    lessons = []
    cur = None
    for p in info:
        explanation = ('page' in p['toks']) and p['hdr'] and p['ftr'] and not re.fullmatch(r'(?i)classwork|homework', p['badge'])
        if not explanation:
            cur = None
            continue
        key = (p['cls'], p['lesson_label'], p['badge'])
        if cur is None or cur['key'] != key:
            unit = '5'
            if 'theme-unit-6' in p['toks']:
                unit = '6'
            elif 'theme-unit-7' in p['toks']:
                unit = '7'
            cur = {'key': key, 'unit': unit, 'label': p['lesson_label'], 'title': p['badge'], 'pages': []}
            lessons.append(cur)
        cur['pages'].append(p)
    return lessons


def lesson_blocks(lesson):
    out = []
    for p in lesson['pages']:
        for b in p['blocks']:
            out.append((p, b))
    return out


def structure(text):
    lessons = parse_book(text)
    res = []
    for i, l in enumerate(lessons):
        blocks = []
        for j, (p, b) in enumerate(lesson_blocks(l)):
            snippet = re.sub(r'\s+', ' ', strip_tags(text[b['start']:b['end']])).strip()[:120]
            blocks.append({'idx': j, 'type': block_type(b['cls']), 'text': snippet})
        res.append({'id': i, 'unit': l['unit'], 'label': l['label'], 'title': l['title'], 'blocks': blocks})
    return res


# ----------------------------------------------------------------------------
# 2. Component templates
# ----------------------------------------------------------------------------
def esc(s):
    return htmllib.escape(s or '', quote=False)


def rich(s):
    """escape + **bold**"""
    s = esc(s)
    return re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)


def lines_html(s):
    ls = [l.strip() for l in (s or '').replace('\r', '').split('\n') if l.strip()]
    return '<br/>'.join(rich(l) for l in ls)


def math(s):
    """tiny math syntax:  [a / b] fraction,  {{x}} result badge,  x_sub,  x^sup,  = signs"""
    s = esc(s or '')
    for _ in range(3):
        s = re.sub(r'\[([^\[\]]+?)\s/\s([^\[\]]+?)\]',
                   r'<span class="math-frac"><span class="math-num">\1</span><span class="math-den">\2</span></span>', s)
    s = re.sub(r'\{\{(.+?)\}\}', r'<span class="math-result">\1</span>', s)
    s = re.sub(r'(?<=\w)_(\w+)', r'<sub>\1</sub>', s)
    s = re.sub(r'\^(\w+)', r'<sup>\1</sup>', s)
    s = s.replace(' = ', ' <span class="math-eq">=</span> ')
    s = s.replace(' - ', ' − ')
    return '<span class="math-expr">' + s + '</span>'


def c_heading(d):
    return '<div class="sec-heading"><span class="sec-heading-en">%s</span></div>' % esc(d.get('title'))


def c_paragraph(d):
    out = '<div class="lead-paragraph">%s</div>' % rich(d.get('en'))
    if (d.get('ar') or '').strip():
        out += NL + ('<div class="lead-paragraph-ar" dir="rtl" style="font-family:\'Cairo\',sans-serif;font-size:12.5px;'
                     'color:#0369a1;font-weight:600;margin:-4px 0 10px 0;line-height:1.6;">%s</div>' % rich(d.get('ar')))
    return out


def c_notes(d):
    label = esc(d.get('label') or 'Notes')
    en = lines_html(d.get('en'))
    ar = lines_html(d.get('ar'))
    s = ['<div class="note-lightbulb-box">',
         '<img alt="Notes Mascot" class="mascot-thumb-transparent" src="mascots_transparent_bg/mascot_lightbulb_transparent.png"/>',
         '<div class="note-text-area">',
         '<div class="note-badge-title">%s</div>' % label]
    if en:
        s.append('<div class="note-body">%s</div>' % en)
    if ar:
        s.append('<div class="note-body-ar">%s</div>' % ar)
    s += ['</div>', '</div>']
    return NL.join(s)


def c_concept(d):
    s = ['<div class="concept-card"><span class="concept-card-tag">%s</span>' % esc(d.get('tag') or 'KEY CONCEPT'),
         '<div class="concept-card-title">%s</div>' % esc(d.get('title')),
         '<div class="concept-card-en">%s</div>' % rich(d.get('en'))]
    if (d.get('ar') or '').strip():
        s.append('<div class="concept-card-ar">%s</div>' % rich(d.get('ar')))
    s.append('</div>')
    return ''.join(s)


def cell_html(v):
    return rich(v)


def c_table(d):
    cols = d.get('columns') or []
    rows = d.get('rows') or []
    rtl = [bool(c.get('rtl')) for c in cols]
    head = ''.join('<th>%s</th>' % esc(c.get('name')) for c in cols)
    body = ''
    for r in rows:
        is_example_row = bool(r and 'مثال' in (r[0] or ''))
        tds = ''
        for i, v in enumerate(r):
            if i >= len(cols):
                break
            is_rtl = rtl[i] or is_example_row
            style = ' style="direction: rtl; text-align: right;"' if is_rtl else ''
            inner = cell_html(v)
            if i == 0 and (not rtl[i] or is_example_row):
                inner = '<strong>%s</strong>' % inner
            tds += '<td%s>%s</td>' % (style, inner)
        body += '<tr>' + tds + '</tr>'
    s = ['<div class="comparison-section">']
    if d.get('with_header', True):
        s += ['<div class="comparison-header"><img alt="Comparison Mascot" src="mascots_transparent_bg/mascot_comparison_transparent.png"/>',
              '<div class="comparison-intro"><h4>%s</h4><p>%s</p></div></div>' % (esc(d.get('title') or 'Comparison'), esc(d.get('subtitle') or 'Key differences at a glance'))]
    s.append('<table class="styled-table"><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % (head, body))
    return ''.join(s)


def c_flow(d):
    steps = d.get('steps') or []
    nodes = ''.join('<div class="process-step-node"><div class="process-step-title">%s</div><div class="process-step-desc">%s</div></div>'
                    % (esc(s.get('title')), esc(s.get('desc'))) for s in steps)
    return NL.join(['<div class="egy-reflection-box">',
                    '<img alt="Mechanism Mascot" class="reflection-thumb-transparent" src="mascots_transparent_bg/mascot_reflection_transparent.png"/>',
                    '<div class="egy-reflection-text">',
                    '<div class="egy-reflection-header"><span>%s</span></div>' % esc(d.get('header')),
                    '<div class="arrow-process-diagram">%s</div>' % nodes,
                    '</div>', '</div>'])


def c_example(d):
    bullets = [l.strip() for l in (d.get('bullets') or '').replace('\r', '').split('\n') if l.strip()]
    bhtml = ''
    for b in bullets:
        if ' = ' in b:
            a, c = b.split(' = ', 1)
            bhtml += '<div>• <strong>%s</strong> = %s</div>' % (esc(a), rich(c))
        else:
            bhtml += '<div>• %s</div>' % rich(b)
    s = ['<div class="real-world-example-box">',
         '<img alt="Example Mascot" class="example-thumb-transparent" src="mascots_transparent_bg/mascot_example_transparent.png"/>',
         '<div class="real-world-example-text">',
         '<div class="real-world-example-header">%s</div>' % esc(d.get('header') or 'مثال من الواقع'),
         '<div class="real-world-example-body">%s</div>' % lines_html(d.get('body'))]
    if bhtml:
        s.append('<div class="real-world-example-breakdown">%s</div>' % bhtml)
    s += ['</div>', '</div>']
    return NL.join(s)


def c_rules(d):
    cards = ''
    for r in d.get('rules') or []:
        cards += NL.join(['<div class="rule-card">',
                          '<div class="rule-name">%s <span class="rule-name-ar">%s</span></div>' % (esc(r.get('name')), esc(r.get('name_ar'))),
                          '<div class="rule-formula-display">%s</div>' % math(r.get('formula')),
                          ('<div class="rule-note-ar">%s</div>' % rich(r.get('note_ar'))) if (r.get('note_ar') or '').strip() else '',
                          '</div>', ''])
    return NL.join(['<div class="rules-box">', '<div class="rules-header">',
                    '<img alt="Rules Mascot" class="rules-mascot" src="mascots_transparent_bg/mascot_rules_transparent.png"/>',
                    '<div class="problems-title-wrap">',
                    '<span class="problems-badge">%s</span>' % esc(d.get('badge') or 'Rules & Formulas'),
                    '<div class="problems-title-en">%s</div>' % esc(d.get('title_en')),
                    '<div class="problems-title-ar">%s</div>' % esc(d.get('title_ar')),
                    '</div>', '</div>', '<div class="rules-grid">', cards + '</div>', '</div>'])


def c_problems(d):
    cards = ''
    for p in d.get('problems') or []:
        steps = ''
        for ln in (p.get('steps') or '').replace('\r', '').split('\n'):
            ln = ln.strip()
            if not ln:
                continue
            if '|' in ln:
                lab, expr = ln.split('|', 1)
            else:
                lab, expr = '', ln
            steps += '<div class="problem-step-row"><span class="problem-step-label">%s</span>%s</div>' % (esc(lab.strip()), math(expr.strip()))
        cards += NL.join(['<div class="problem-card">',
                          '<div class="problem-card-head"><span class="problem-card-name">%s</span><span class="problem-card-name-ar">%s</span></div>' % (esc(p.get('name')), esc(p.get('name_ar'))),
                          '<div class="problem-given">%s</div>' % rich(p.get('given')),
                          '<div class="problem-steps">%s</div>' % steps,
                          ('<div class="problem-explain-ar">%s</div>' % rich(p.get('explain_ar'))) if (p.get('explain_ar') or '').strip() else '',
                          '</div>', ''])
    return NL.join(['<div class="problems-box">', '<div class="problems-header">',
                    '<img alt="Problems Mascot" class="problems-mascot" src="mascots_transparent_bg/mascot_problems_transparent.png"/>',
                    '<div class="problems-title-wrap">',
                    '<span class="problems-badge">%s</span>' % esc(d.get('badge') or 'Worked Problems'),
                    '<div class="problems-title-en">%s</div>' % esc(d.get('title_en')),
                    '<div class="problems-title-ar">%s</div>' % esc(d.get('title_ar')),
                    '</div>', '</div>', '<div class="problems-grid">', cards + '</div>', '</div>'])


RENDERERS = {
    'heading': c_heading, 'paragraph': c_paragraph, 'notes': c_notes, 'concept': c_concept, 'table': c_table,
    'flow': c_flow, 'example': c_example, 'rules': c_rules, 'problems': c_problems,
}


def render(kind, data):
    if kind == 'raw':
        return data.get('html') or ''
    if kind not in RENDERERS:
        raise ValueError('unknown component: %s' % kind)
    return RENDERERS[kind](data)


def unrich(html_str):
    s = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', html_str or '', flags=re.S)
    s = re.sub(r'<code[^>]*>(.*?)</code>', r'\1', s, flags=re.S)
    s = re.sub(r'<[^>]+>', '', s)
    return htmllib.unescape(re.sub(r'\s+', ' ', s)).strip()


def unlines(html_str):
    parts = re.split(r'<br\s*/?>', html_str or '', flags=re.I)
    return '\n'.join(unrich(p) for p in parts if unrich(p))


def unmath(html_str):
    s = html_str or ''
    for _ in range(3):
        s = re.sub(r'<span class="math-frac">\s*<span class="math-num">(.*?)</span>\s*<span class="math-den">(.*?)</span>\s*</span>',
                   lambda m: '[%s / %s]' % (unrich(m.group(1)), unrich(m.group(2))), s, flags=re.S)
    s = re.sub(r'<span class="math-result">(.*?)</span>', lambda m: '{{%s}}' % unrich(m.group(1)), s, flags=re.S)
    s = re.sub(r'<sub>(.*?)</sub>', lambda m: '_' + unrich(m.group(1)), s, flags=re.S)
    s = re.sub(r'<sup>(.*?)</sup>', lambda m: '^' + unrich(m.group(1)), s, flags=re.S)
    s = re.sub(r'<span class="math-eq">\s*=\s*</span>', ' = ', s, flags=re.S)
    s = re.sub(r'<[^>]+>', '', s)
    s = htmllib.unescape(re.sub(r'\s+', ' ', s)).strip()
    return s.replace(' − ', ' - ').replace('−', '-')


def first_class(node, cls_name):
    for ch in node['children']:
        if cls_name in ch['cls'].split():
            return ch
        found = first_class(ch, cls_name)
        if found:
            return found
    return None


def all_class(node, cls_name):
    out = []
    for ch in node['children']:
        if cls_name in ch['cls'].split():
            out.append(ch)
        out.extend(all_class(ch, cls_name))
    return out


def extract_block(lesson_id, block_idx):
    text = read_book()
    lessons = parse_book(text)
    if lesson_id < 0 or lesson_id >= len(lessons):
        raise ValueError('lesson not found')
    blocks = lesson_blocks(lessons[lesson_id])
    if block_idx < 0 or block_idx >= len(blocks):
        raise ValueError('block index out of range')
    b = blocks[block_idx][1]
    toks = b['cls'].split()
    inner = lambda n: text[n['start']:n['end']] if n else ''

    if 'sec-heading' in toks:
        sp = first_class(b, 'sec-heading-en')
        return {'kind': 'heading', 'data': {'title': unrich(inner(sp) or inner(b))}}

    if 'lead-paragraph' in toks:
        ar = ''
        if block_idx + 1 < len(blocks) and 'lead-paragraph-ar' in blocks[block_idx + 1][1]['cls'].split():
            ar = unrich(inner(blocks[block_idx + 1][1]))
        return {'kind': 'paragraph', 'data': {'en': unrich(inner(b)), 'ar': ar}}

    if 'note-lightbulb-box' in toks:
        lbl = first_class(b, 'note-badge-title')
        en = first_class(b, 'note-body')
        ar = first_class(b, 'note-body-ar')
        return {'kind': 'notes', 'data': {'label': unrich(inner(lbl)) or 'Notes', 'en': unlines(inner(en)), 'ar': unlines(inner(ar))}}

    if 'concept-card' in toks:
        return {'kind': 'concept', 'data': {
            'tag': unrich(inner(first_class(b, 'concept-card-tag'))) or 'KEY CONCEPT',
            'title': unrich(inner(first_class(b, 'concept-card-title'))),
            'en': unrich(inner(first_class(b, 'concept-card-en'))),
            'ar': unrich(inner(first_class(b, 'concept-card-ar'))),
        }}

    if 'comparison-section' in toks:
        hdr = first_class(b, 'comparison-header')
        title = 'Comparison'
        sub = 'Key differences at a glance'
        if hdr:
            intro = first_class(hdr, 'comparison-intro')
            if intro:
                h4s = [c for c in intro['children'] if c['tag'] == 'h4']
                ps = [c for c in intro['children'] if c['tag'] == 'p']
                if h4s:
                    title = unrich(inner(h4s[0]))
                if ps:
                    sub = unrich(inner(ps[0]))
        cols = []
        tbl = first_class(b, 'styled-table') or b
        thead = next((c for c in tbl['children'] if c['tag'] == 'thead'), None)
        tbody = next((c for c in tbl['children'] if c['tag'] == 'tbody'), None)
        if thead:
            ths = [c for tr in thead['children'] if tr['tag'] == 'tr' for c in tr['children'] if c['tag'] == 'th']
            for th in ths:
                cols.append({'name': unrich(inner(th)), 'rtl': False})
        rows = []
        if tbody:
            for tr in tbody['children']:
                if tr['tag'] != 'tr':
                    continue
                tds = [c for c in tr['children'] if c['tag'] == 'td']
                row = []
                for idx_c, td in enumerate(tds):
                    raw_td = inner(td)
                    if idx_c < len(cols) and ('direction: rtl' in raw_td or 'direction:rtl' in raw_td):
                        cols[idx_c]['rtl'] = True
                    val = unrich(raw_td)
                    if idx_c == 0 and idx_c < len(cols) and not cols[idx_c]['rtl'] and val.startswith('**') and val.endswith('**'):
                        val = val[2:-2]
                    row.append(val)
                rows.append(row)
        return {'kind': 'table', 'data': {'title': title, 'subtitle': sub, 'with_header': bool(hdr), 'columns': cols, 'rows': rows}}

    if 'egy-reflection-box' in toks:
        hdr = first_class(b, 'egy-reflection-header')
        steps = []
        for nd in all_class(b, 'process-step-node'):
            steps.append({
                'title': unrich(inner(first_class(nd, 'process-step-title'))),
                'desc': unrich(inner(first_class(nd, 'process-step-desc'))),
            })
        return {'kind': 'flow', 'data': {'header': unrich(inner(hdr)), 'steps': steps}}

    if 'real-world-example-box' in toks:
        hdr = first_class(b, 'real-world-example-header')
        body = first_class(b, 'real-world-example-body')
        brk = first_class(b, 'real-world-example-breakdown')
        bullets = []
        if brk:
            for ch in brk['children']:
                txt = unrich(inner(ch)).lstrip('•').strip()
                txt = re.sub(r'^\*\*(.+?)\*\*\s*=\s*', r'\1 = ', txt)
                if txt:
                    bullets.append(txt)
        return {'kind': 'example', 'data': {'header': unrich(inner(hdr)), 'body': unlines(inner(body)), 'bullets': '\n'.join(bullets)}}

    if 'rules-box' in toks:
        rules = []
        for rc in all_class(b, 'rule-card'):
            rn = first_class(rc, 'rule-name')
            rna = first_class(rc, 'rule-name-ar')
            rn_txt = unrich(inner(rn))
            rna_txt = unrich(inner(rna))
            if rna_txt and rn_txt.endswith(rna_txt):
                rn_txt = rn_txt[:-len(rna_txt)].strip()
            rules.append({
                'name': rn_txt,
                'name_ar': rna_txt,
                'formula': unmath(inner(first_class(rc, 'rule-formula-display'))),
                'note_ar': unrich(inner(first_class(rc, 'rule-note-ar'))),
            })
        return {'kind': 'rules', 'data': {
            'badge': unrich(inner(first_class(b, 'problems-badge'))) or 'Rules & Formulas',
            'title_en': unrich(inner(first_class(b, 'problems-title-en'))),
            'title_ar': unrich(inner(first_class(b, 'problems-title-ar'))),
            'rules': rules,
        }}

    if 'problems-box' in toks:
        probs = []
        for pc in all_class(b, 'problem-card'):
            step_rows = []
            for sr in all_class(pc, 'problem-step-row'):
                lbl = first_class(sr, 'problem-step-label')
                lbl_txt = unrich(inner(lbl))
                rest_html = inner(sr)
                if lbl:
                    rest_html = rest_html.replace(inner(lbl), '', 1)
                expr_txt = unmath(rest_html)
                step_rows.append(('%s | %s' % (lbl_txt, expr_txt)) if lbl_txt else expr_txt)
            probs.append({
                'name': unrich(inner(first_class(pc, 'problem-card-name'))),
                'name_ar': unrich(inner(first_class(pc, 'problem-card-name-ar'))),
                'given': unrich(inner(first_class(pc, 'problem-given'))),
                'steps': '\n'.join(step_rows),
                'explain_ar': unrich(inner(first_class(pc, 'problem-explain-ar'))),
            })
        return {'kind': 'problems', 'data': {
            'badge': unrich(inner(first_class(b, 'problems-badge'))) or 'Worked Problems',
            'title_en': unrich(inner(first_class(b, 'problems-title-en'))),
            'title_ar': unrich(inner(first_class(b, 'problems-title-ar'))),
            'problems': probs,
        }}

    return {'kind': 'raw', 'data': {'html': inner(b)}}


# ----------------------------------------------------------------------------
# 3. Edit operations (always re-parse, always backup first)
# ----------------------------------------------------------------------------
def read_book():
    with open(BOOK, 'r', encoding='utf-8', newline='') as f:
        return f.read()


def backup():
    os.makedirs(BACKUPS, exist_ok=True)
    name = 'book_%s_%06d.html' % (time.strftime('%Y%m%d_%H%M%S'), int((time.time() % 1) * 1000000))
    shutil.copyfile(BOOK, os.path.join(BACKUPS, name))
    files = sorted(os.listdir(BACKUPS))
    for old in files[:-40]:
        try:
            os.remove(os.path.join(BACKUPS, old))
        except OSError:
            pass
    return name


def write_book(text):
    with open(BOOK, 'w', encoding='utf-8', newline='') as f:
        f.write(text)


def do_insert(lesson_id, after, kind, data):
    text = read_book()
    lessons = parse_book(text)
    if lesson_id < 0 or lesson_id >= len(lessons):
        raise ValueError('lesson not found')
    l = lessons[lesson_id]
    blocks = lesson_blocks(l)
    snippet = render(kind, data).replace('\r\n', '\n').replace('\n', NL)
    if after == 'start' or not blocks:
        pos = l['pages'][0]['hdr']['end']
    elif after == 'end':
        # end of the last block of the lesson
        pos = blocks[-1][1]['end']
    else:
        k = int(after)
        if k < 0 or k >= len(blocks):
            raise ValueError('block index out of range')
        pos = blocks[k][1]['end']
    new = text[:pos] + NL + snippet + text[pos:]
    backup()
    write_book(new)
    return snippet


def do_delete(lesson_id, block_idx):
    text = read_book()
    lessons = parse_book(text)
    l = lessons[lesson_id]
    blocks = lesson_blocks(l)
    b = blocks[block_idx][1]
    s, e = b['start'], b['end']
    # also eat the line break before the block
    while s > 0 and text[s - 1] in ' \t':
        s -= 1
    if text[max(0, s - 2):s] == NL:
        s -= 2
    new = text[:s] + text[e:]
    backup()
    write_book(new)


def do_update(lesson_id, block_idx, kind, data):
    text = read_book()
    lessons = parse_book(text)
    if lesson_id < 0 or lesson_id >= len(lessons):
        raise ValueError('lesson not found')
    blocks = lesson_blocks(lessons[lesson_id])
    if block_idx < 0 or block_idx >= len(blocks):
        raise ValueError('block index out of range')
    b = blocks[block_idx][1]
    s, e = b['start'], b['end']
    if kind == 'paragraph' and 'lead-paragraph' in b['cls'].split():
        if block_idx + 1 < len(blocks) and 'lead-paragraph-ar' in blocks[block_idx + 1][1]['cls'].split():
            e = blocks[block_idx + 1][1]['end']
    snippet = render(kind, data).replace('\r\n', '\n').replace('\n', NL)
    new = text[:s] + snippet + text[e:]
    backup()
    write_book(new)
    return snippet


def do_undo():
    if not os.path.isdir(BACKUPS):
        raise ValueError('no backups')
    files = sorted(f for f in os.listdir(BACKUPS) if f.endswith('.html'))
    if not files:
        raise ValueError('nothing to undo')
    last = files[-1]
    shutil.copyfile(os.path.join(BACKUPS, last), BOOK)
    os.remove(os.path.join(BACKUPS, last))
    return last


def preview_doc(kind, data, unit):
    text = read_book()
    head = text[:text.index('</head>')] + '</head>'
    snippet = render(kind, data)
    theme = 'theme-unit-%s' % unit
    return (head + '<body style="padding:12px;background:#fff"><div class="container %s"><div class="page %s" '
            'style="height:auto;min-height:0;max-height:none;box-shadow:none;border-radius:0;padding:6px 10px;width:auto;">%s</div></div></body></html>'
            % (theme, theme, snippet))


# ----------------------------------------------------------------------------
# 4. HTTP server
# ----------------------------------------------------------------------------
MIME = {'.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'application/javascript', '.png': 'image/png',
        '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.svg': 'image/svg+xml', '.json': 'application/json', '.woff2': 'font/woff2'}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body, ctype='application/json; charset=utf-8'):
        if isinstance(body, str):
            body = body.encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def jerr(self, e):
        self.send(400, json.dumps({'ok': False, 'error': str(e)}, ensure_ascii=False))

    def do_GET(self):
        path = unquote(urlparse(self.path).path)
        if path in ('/', '/index.html'):
            with open(os.path.join(HERE, 'index.html'), 'rb') as f:
                return self.send(200, f.read(), 'text/html; charset=utf-8')
        if path == '/api/structure':
            try:
                return self.send(200, json.dumps({'ok': True, 'lessons': structure(read_book())}, ensure_ascii=False))
            except Exception as e:
                return self.jerr(e)
        if path == '/api/block':
            try:
                qs = parse_qs(urlparse(self.path).query)
                res = extract_block(int(qs['lesson'][0]), int(qs['block'][0]))
                return self.send(200, json.dumps({'ok': True, **res}, ensure_ascii=False))
            except Exception as e:
                return self.jerr(e)
        if path.startswith('/files/'):
            rel = path[len('/files/'):]
            full = os.path.normpath(os.path.join(KIT, rel))
            if not full.startswith(KIT) or not os.path.isfile(full):
                return self.send(404, 'not found', 'text/plain')
            ext = os.path.splitext(full)[1].lower()
            with open(full, 'rb') as f:
                return self.send(200, f.read(), MIME.get(ext, 'application/octet-stream'))
        self.send(404, 'not found', 'text/plain')

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            n = int(self.headers.get('Content-Length', '0'))
            body = json.loads(self.rfile.read(n).decode('utf-8') or '{}')
        except Exception as e:
            return self.jerr(e)
        try:
            if path == '/api/insert':
                snip = do_insert(int(body['lesson']), body.get('after', 'end'), body['kind'], body.get('data') or {})
                return self.send(200, json.dumps({'ok': True, 'snippet': snip}, ensure_ascii=False))
            if path == '/api/update':
                snip = do_update(int(body['lesson']), int(body['block']), body['kind'], body.get('data') or {})
                return self.send(200, json.dumps({'ok': True, 'snippet': snip}, ensure_ascii=False))
            if path == '/api/delete':
                do_delete(int(body['lesson']), int(body['block']))
                return self.send(200, json.dumps({'ok': True}))
            if path == '/api/undo':
                return self.send(200, json.dumps({'ok': True, 'restored': do_undo()}))
            if path == '/api/preview':
                doc = preview_doc(body['kind'], body.get('data') or {}, str(body.get('unit', '5')))
                return self.send(200, doc, 'text/html; charset=utf-8')
        except Exception as e:
            return self.jerr(e)
        self.send(404, '{}')


if __name__ == '__main__':
    srv = ThreadingHTTPServer(('127.0.0.1', PORT), H)
    print('Book Builder running on http://127.0.0.1:%d  (Ctrl+C to stop)' % PORT)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
