"""
Build the classroom PowerPoint from the editable export.

    from deckgen import classpoint
    classpoint.build(Path('export/week02.pptx'), footer='SD5913 · PFAD',
                     activities=Path('export/week02-activities.json'))
    -> export/week02-classpoint.pptx

Adds, in one pass, with only the standard library:
  1. ait4x theme + slide master (footer, slide number, orange dot bullets,
     PolyU Design mark) + 8 layouts: Title, Section band, Content white,
     Content ink, Two column, Question, Quote, Statement.

    classpoint.template(Path('export/ait4x-template.potx'), footer='SD5913 · PFAD')
     -> standalone template (.potx) with one sample slide per layout.
  2. Static font names for weights — PowerPoint has no weight axis, so bold
     runs >= 88px become "Inter Black", >= 44px become "Inter ExtraBold".
  3. Row-by-row fade + float-up entrance on every slide, auto-starting.
  4. ClassPoint buttons + activity tags from the deck's activity manifest
     (format from https://github.com/venetanji/classpoint.py). Button artwork:
     btn-*.png in the package's assets/.

Everything that is per-course — the footer text — is a parameter. Nothing here
reads the environment or the filesystem outside the package.
"""
import html, json, re, zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / 'assets'   # button artwork + the PolyU Design mark
RT = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
NS = ('xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
      'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"')
PX = 6350  # EMU per px at 1920x1080 (13.333 in wide slide: 1 px = 0.5 pt, so sz = px * 50)

# ───────────────────────── theme / master / layouts ─────────────────────────
THEME = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="ait4x"><a:themeElements>
<a:clrScheme name="ait4x"><a:dk1><a:srgbClr val="000B1C"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1><a:dk2><a:srgbClr val="2A323D"/></a:dk2><a:lt2><a:srgbClr val="F4F4F2"/></a:lt2><a:accent1><a:srgbClr val="64C2C3"/></a:accent1><a:accent2><a:srgbClr val="ED6D24"/></a:accent2><a:accent3><a:srgbClr val="943890"/></a:accent3><a:accent4><a:srgbClr val="146AB5"/></a:accent4><a:accent5><a:srgbClr val="F6AD00"/></a:accent5><a:accent6><a:srgbClr val="6FBA2C"/></a:accent6><a:hlink><a:srgbClr val="00544C"/></a:hlink><a:folHlink><a:srgbClr val="5C6470"/></a:folHlink></a:clrScheme>
<a:fontScheme name="ait4x"><a:majorFont><a:latin typeface="Inter Black"/><a:ea typeface=""/><a:cs typeface=""/></a:majorFont><a:minorFont><a:latin typeface="Inter"/><a:ea typeface=""/><a:cs typeface=""/></a:minorFont></a:fontScheme>
<a:fmtScheme name="ait4x"><a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst><a:lnStyleLst><a:ln w="12700"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln><a:ln w="19050"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln><a:ln w="25400"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst><a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst><a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst></a:fmtScheme>
</a:themeElements><a:objectDefaults/><a:extraClrSchemeLst/></a:theme>'''

# PowerPoint stores typeface + b/i flags only; the family name carries the weight.
# Windows exposes a variable font's named instances as these legacy families
# (verified from the fvar table of Inter-VariableFont_opsz,wght.ttf). Google's
# static ZIP is named 'Inter 18pt …' — never target those names. See ../PPTX-EXPORT.md.
WEIGHT_TO_FAMILY = {100: 'Inter Thin', 200: 'Inter ExtraLight', 300: 'Inter Light', 400: 'Inter',
                    500: 'Inter Medium', 600: 'Inter SemiBold', 700: 'Inter',  # 700 = 'Inter' + b="1"
                    800: 'Inter ExtraBold', 900: 'Inter Black'}
BLACK, XBOLD, TEXT, MONO = 'Inter Black', 'Inter ExtraBold', 'Inter', 'JetBrains Mono'


def box(x, y, w, h):
    return f'<a:xfrm><a:off x="{x * PX}" y="{y * PX}"/><a:ext cx="{w * PX}" cy="{h * PX}"/></a:xfrm>'


def ph(i, name, typ, idx, geo, size, font, color, bold=False, spc=0, caps=False, anchor='t', lh=100, algn='l', body=None):
    t = f' type="{typ}"' if typ else ''
    x = f' idx="{idx}"' if idx is not None else ''
    return (f'<p:sp><p:nvSpPr><p:cNvPr id="{i}" name="{name}"/><p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr>'
            f'<p:nvPr><p:ph{t}{x}/></p:nvPr></p:nvSpPr><p:spPr>{geo}<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr>'
            f'<p:txBody><a:bodyPr wrap="square" lIns="0" tIns="0" rIns="0" bIns="0" anchor="{anchor}"><a:normAutofit/></a:bodyPr>'
            f'<a:lstStyle><a:lvl1pPr marL="0" indent="0" algn="{algn}"><a:lnSpc><a:spcPct val="{lh * 1000}"/></a:lnSpc><a:buNone/>'
            f'<a:defRPr sz="{round(size * 50)}" b="{1 if bold else 0}" spc="{spc}" cap="{"all" if caps else "none"}">'
            f'<a:solidFill><a:srgbClr val="{color}"/></a:solidFill><a:latin typeface="{font}"/></a:defRPr></a:lvl1pPr></a:lstStyle>'
            f'{body or "<a:p><a:endParaRPr/></a:p>"}</p:txBody></p:sp>')


SLDNUM = '<a:p><a:fld id="{B6F15528-21DE-4FAA-801E-634DDDAF4B2B}" type="slidenum"><a:rPr lang="en-US"/><a:t>‹#›</a:t></a:fld></a:p>'


def chrome(footer, muted, logo=False):
    """Eyebrow + footer + slide number (+ PolyU Design wordmark on white layouts)."""
    parts = [ph(2, 'Eyebrow', 'body', 10, box(120, 96, 1500, 40), 24, MONO, muted, spc=340, caps=True),
             ph(20, 'Footer', 'ftr', 11, box(120, 1000, 1000, 32), 22, MONO, muted, spc=340, caps=True, anchor='b',
                body=f'<a:p><a:r><a:rPr lang="en-US"/><a:t>{html.escape(footer)}</a:t></a:r></a:p>'),
             ph(21, 'Slide number', 'sldNum', 12, box(1400, 1000, 400, 32), 22, MONO, muted, spc=340, anchor='b', algn='r', body=SLDNUM)]
    if logo:  # rId2 in the layout rels -> ../media/polyu-design-logo.png
        parts.append('<p:pic><p:nvPicPr><p:cNvPr id="22" name="PolyU Design"/><p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr><p:nvPr userDrawn="1"/></p:nvPicPr>'
                     '<p:blipFill><a:blip r:embed="rId2"/><a:stretch><a:fillRect/></a:stretch></p:blipFill>'
                     f'<p:spPr>{box(1668, 74, 132, 88)}<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>')
    return parts


def wordmark(color, y=1000):
    """a·t4x — typographic wordmark, X in orange. Plain shape, not a placeholder."""
    run = lambda t, c: f'<a:r><a:rPr lang="en-US" sz="1600" b="1" spc="-100"><a:solidFill><a:srgbClr val="{c}"/></a:solidFill><a:latin typeface="{BLACK}"/></a:rPr><a:t>{t}</a:t></a:r>'
    return (f'<p:sp><p:nvSpPr><p:cNvPr id="23" name="ait4x"/><p:cNvSpPr txBox="1"/><p:nvPr userDrawn="1"/></p:nvSpPr>'
            f'<p:spPr>{box(1600, y, 200, 32)}<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr>'
            f'<p:txBody><a:bodyPr wrap="none" lIns="0" tIns="0" rIns="0" bIns="0" anchor="b"/><a:lstStyle/><a:p><a:pPr algn="r"/>{run("a·t4", color)}{run("x", "ED6D24")}</a:p></p:txBody></p:sp>')


def layout(name, bg, parts, kind='obj'):
    return (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<p:sldLayout {NS} type="{kind}" preserve="1">'
            f'<p:cSld name="{name}"><p:bg><p:bgPr><a:solidFill><a:srgbClr val="{bg}"/></a:solidFill><a:effectLst/></p:bgPr></p:bg>'
            '<p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
            + ''.join(parts) + '</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>')


INK, WHITE, VIOLET, PAPER = '000B1C', 'FFFFFF', '943890', 'F4F4F2'
MUTED_L, MUTED_D, TXT = 'B3B7BE', '5C6470', '2A323D'
# (name, background, uses logo, xml) — the footer text is baked into the chrome,
# so the set is built per course rather than held as a module constant.
def layouts(footer):
    return [
         ('Title', INK, False, layout('Title', INK, [
            ph(2, 'Eyebrow', 'body', 10, box(120, 560, 1500, 40), 24, MONO, MUTED_L, spc=340, caps=True),
            ph(3, 'Title', 'ctrTitle', None, box(120, 620, 1680, 300), 150, BLACK, WHITE, True, anchor='b', lh=88),
            ph(4, 'Subtitle', 'subTitle', 1, box(120, 940, 1400, 60), 36, TEXT, 'D3E7E8'),
            wordmark(WHITE, 968)], 'title')),
        ('Section band', VIOLET, False, layout('Section band', VIOLET, [
            ph(2, 'Eyebrow', 'body', 10, box(120, 560, 1500, 40), 24, MONO, 'F2ECF5', spc=340, caps=True),
            ph(3, 'Title', 'title', None, box(120, 620, 1680, 300), 130, BLACK, WHITE, True, anchor='b', lh=88),
            ph(4, 'Kicker', 'body', 1, box(120, 940, 1400, 60), 28, MONO, 'F2ECF5', spc=340, caps=True),
            ph(21, 'Slide number', 'sldNum', 12, box(1400, 1000, 400, 32), 22, MONO, 'F2ECF5', spc=340, anchor='b', algn='r', body=SLDNUM)], 'secHead')),
        ('Content — white', WHITE, True, layout('Content — white', WHITE, chrome(footer, MUTED_D, True) + [
            ph(3, 'Title', 'title', None, box(120, 184, 1680, 140), 72, XBOLD, INK, True, lh=95),
            ph(4, 'Body', 'body', 1, box(120, 372, 1680, 580), 36, TEXT, TXT, lh=140)])),
        ('Content — ink', INK, False, layout('Content — ink', INK, chrome(footer, MUTED_L) + [
            ph(3, 'Title', 'title', None, box(120, 184, 1680, 200), 110, BLACK, WHITE, True, lh=90),
            ph(4, 'Body', 'body', 1, box(120, 430, 1680, 520), 36, TEXT, 'D3E7E8', lh=140)])),
        ('Two column', WHITE, True, layout('Two column', WHITE, chrome(footer, MUTED_D, True) + [
            ph(3, 'Title', 'title', None, box(120, 184, 800, 260), 72, XBOLD, INK, True, lh=95),
            ph(4, 'Body', 'body', 1, box(120, 480, 800, 470), 36, TEXT, TXT, lh=140),
            ph(5, 'Picture', 'pic', 2, box(1000, 184, 800, 766), 28, TEXT, MUTED_D)], 'twoObj')),
        ('Question', WHITE, True, layout('Question', WHITE, chrome(footer, MUTED_D, True) + [
            ph(3, 'Question', 'title', None, box(120, 300, 1680, 380), 120, BLACK, INK, True, anchor='ctr', lh=90),
            ph(4, 'Choices', 'body', 1, box(120, 720, 1300, 220), 36, TEXT, INK, lh=130)])),
        ('Quote', PAPER, True, layout('Quote', PAPER, chrome(footer, MUTED_D, True) + [
            ph(3, 'Quote', 'body', 1, box(120, 300, 1600, 500), 88, XBOLD, INK, True, anchor='ctr', lh=100),
            ph(4, 'Attribution', 'body', 2, box(120, 840, 1600, 40), 28, MONO, MUTED_D)])),
        ('Statement', INK, False, layout('Statement', INK, chrome(footer, MUTED_L) + [
            ph(3, 'Statement', 'title', None, box(120, 184, 1680, 760), 150, BLACK, WHITE, True, anchor='ctr', lh=88)])),
        ]


BOLD_ATTR = ' b="1"'  # kept out of the f-string for Python < 3.12


def master(layout_rids, theme_rid, footer):
    ids = ''.join(f'<p:sldLayoutId id="{2147483649 + i}" r:id="{r}"/>' for i, r in enumerate(layout_rids))
    def rpr(sz, font, color, extra=''):
        return f'<a:defRPr sz="{sz}"{extra}><a:solidFill><a:srgbClr val="{color}"/></a:solidFill><a:latin typeface="{font}"/></a:defRPr>'
    title = f'<a:lvl1pPr marL="0" indent="0" algn="l"><a:lnSpc><a:spcPct val="95000"/></a:lnSpc><a:buNone/>{rpr(3600, XBOLD, INK, BOLD_ATTR)}</a:lvl1pPr>'
    # body: level 1 plain, levels 2-3 use the dot (the wordmark's invisible i) in orange as bullet
    body = (f'<a:lvl1pPr marL="0" indent="0" algn="l"><a:lnSpc><a:spcPct val="140000"/></a:lnSpc><a:spcBef><a:spcPts val="600"/></a:spcBef><a:buNone/>{rpr(1800, TEXT, TXT)}</a:lvl1pPr>'
            f'<a:lvl2pPr marL="{48 * PX}" indent="{-48 * PX}" algn="l"><a:lnSpc><a:spcPct val="140000"/></a:lnSpc><a:buClr><a:srgbClr val="ED6D24"/></a:buClr><a:buFont typeface="{BLACK}"/><a:buChar char="·"/>{rpr(1800, TEXT, TXT)}</a:lvl2pPr>'
            f'<a:lvl3pPr marL="{96 * PX}" indent="{-48 * PX}" algn="l"><a:lnSpc><a:spcPct val="140000"/></a:lnSpc><a:buClr><a:srgbClr val="ED6D24"/></a:buClr><a:buFont typeface="{BLACK}"/><a:buChar char="·"/>{rpr(1400, TEXT, MUTED_D)}</a:lvl3pPr>')
    other = f'<a:lvl1pPr marL="0" indent="0" algn="l"><a:buNone/>{rpr(1800, TEXT, INK)}</a:lvl1pPr>'
    return (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<p:sldMaster {NS}><p:cSld><p:bg><p:bgPr><a:solidFill><a:srgbClr val="{WHITE}"/></a:solidFill><a:effectLst/></p:bgPr></p:bg>'
            '<p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
            + ph(2, 'Title', 'title', None, box(120, 184, 1680, 140), 72, XBOLD, INK, True, lh=95)
            + ph(3, 'Body', 'body', 1, box(120, 372, 1680, 580), 36, TEXT, TXT, lh=140)
            + ''.join(chrome(footer, MUTED_D)[1:])
            + '</p:spTree></p:cSld><p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>'
            f'<p:sldLayoutIdLst>{ids}</p:sldLayoutIdLst><p:hf hdr="0" dt="0"/><p:txStyles><p:titleStyle>{title}</p:titleStyle>'
            f'<p:bodyStyle>{body}</p:bodyStyle><p:otherStyle>{other}</p:otherStyle></p:txStyles></p:sldMaster>')


def layout_rels(with_logo):
    img = f'<Relationship Id="rId2" Type="{RT}image" Target="../media/polyu-design-logo.png"/>' if with_logo else ''
    return (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'<Relationship Id="rId1" Type="{RT}slideMaster" Target="../slideMasters/slideMaster1.xml"/>{img}</Relationships>')


def install_master(parts, ct, footer, first_layout=2):
    """Write theme, master and layouts into the parts dict. Returns updated [Content_Types] xml."""
    parts['ppt/theme/theme1.xml'] = THEME.encode()
    parts['ppt/media/polyu-design-logo.png'] = (ASSETS / 'polyu-design-logo.png').read_bytes()
    rids = ['rId1'] if first_layout == 2 else []
    LAYOUTS = layouts(footer)
    for i, (name, bg, logo, xml) in enumerate(LAYOUTS, start=first_layout):
        parts[f'ppt/slideLayouts/slideLayout{i}.xml'] = xml.encode()
        parts[f'ppt/slideLayouts/_rels/slideLayout{i}.xml.rels'] = layout_rels(logo).encode()
        rids.append(f'rId{len(rids) + 1}')
        ct = ct.replace('</Types>', f'<Override PartName="/ppt/slideLayouts/slideLayout{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/></Types>')
    theme_rid = f'rId{len(rids) + 1}'
    parts['ppt/slideMasters/slideMaster1.xml'] = master(rids, theme_rid, footer).encode()
    parts['ppt/slideMasters/_rels/slideMaster1.xml.rels'] = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + ''.join(f'<Relationship Id="{r}" Type="{RT}slideLayout" Target="../slideLayouts/slideLayout{i + first_layout - (1 if first_layout == 2 else 0)}.xml"/>' for i, r in enumerate(rids))
        + f'<Relationship Id="{theme_rid}" Type="{RT}theme" Target="../theme/theme1.xml"/></Relationships>').encode()
    if 'Extension="png"' not in ct:
        ct = ct.replace('</Types>', '<Default Extension="png" ContentType="image/png"/></Types>')
    return ct


# ───────────────────────── fonts ─────────────────────────
def fix_fonts(xml):
    def run(m):
        attrs, inner = m.group(1), m.group(2)
        if 'b="1"' not in attrs or 'typeface="Inter"' not in inner:
            return m.group(0)
        sz = int((re.search(r' sz="(\d+)"', attrs) or [0, 0])[1])
        fam = BLACK if sz >= 4400 else XBOLD if sz >= 2200 else None
        if not fam:
            return m.group(0)
        inner2 = inner.replace('typeface="Inter"', f'typeface="{fam}"')
        return f'<a:rPr{attrs}>{inner2}</a:rPr>'
    return re.sub(r'<a:rPr([^>]*)>(.*?)</a:rPr>', run, xml, flags=re.S)


# ───────────────────────── animation ─────────────────────────
DUR, GAP, BAND = 500, 150, 300000


def shapes(xml):
    out = []
    for m in re.finditer(r'<p:(sp|pic|grpSp|cxnSp)>(.*?)</p:\1>', xml, re.S):
        b = m.group(2)
        i = re.search(r'<p:cNvPr id="(\d+)" name="([^"]*)"', b)
        o = re.search(r'<a:off x="(-?\d+)" y="(-?\d+)"/><a:ext cx="(\d+)" cy="(\d+)"/>', b)
        if i and o:
            out.append((int(i.group(1)), i.group(2), *map(int, o.groups())))
    return out


def bands(sh, w, h):
    # full-slide backgrounds, the ClassPoint button and slide chrome (footer, number, logo) never animate
    keep = sorted((s for s in sh if not (s[4] >= .9 * w and s[5] >= .9 * h) and s[1] != 'btnInknoeActivityCp2' and not s[1].startswith('chrome')), key=lambda s: (s[3], s[2]))
    bs, cur = [], []
    for s in keep:
        if cur and s[3] - cur[0][3] > BAND:
            bs.append(cur); cur = []
        cur.append(s)
    return bs + ([cur] if cur else [])


def effect(nid, spid, delay):
    return (f'<p:par><p:cTn id="{nid}" presetID="10" presetClass="entr" presetSubtype="0" fill="hold" grpId="0" nodeType="withEffect"><p:stCondLst><p:cond delay="{delay}"/></p:stCondLst><p:childTnLst>'
            f'<p:set><p:cBhvr><p:cTn id="{nid+1}" dur="1" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn><p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl><p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst></p:cBhvr><p:to><p:strVal val="visible"/></p:to></p:set>'
            f'<p:animEffect transition="in" filter="fade"><p:cBhvr><p:cTn id="{nid+2}" dur="{DUR}"/><p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl></p:cBhvr></p:animEffect>'
            f'<p:anim calcmode="lin" valueType="num"><p:cBhvr additive="base"><p:cTn id="{nid+3}" dur="{DUR}" fill="hold"/><p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl><p:attrNameLst><p:attrName>ppt_y</p:attrName></p:attrNameLst></p:cBhvr>'
            f'<p:tavLst><p:tav tm="0"><p:val><p:strVal val="#ppt_y+.025"/></p:val></p:tav><p:tav tm="100000"><p:val><p:strVal val="#ppt_y"/></p:val></p:tav></p:tavLst></p:anim></p:childTnLst></p:cTn></p:par>')


def timing(bs):
    nid, eff, bld, delay = 5, '', '', 0
    for b in bs:
        for s in b:
            eff += effect(nid, s[0], delay); nid += 4
            bld += f'<p:bldP spid="{s[0]}" grpId="0"/>'
        delay += DUR + GAP
    return ('<p:timing><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst><p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>'
            '<p:par><p:cTn id="3" fill="hold"><p:stCondLst><p:cond delay="indefinite"/><p:cond evt="onBegin" delay="0"><p:tn val="2"/></p:cond></p:stCondLst><p:childTnLst>'
            f'<p:par><p:cTn id="4" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>{eff}</p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn>'
            '<p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst><p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst></p:seq></p:childTnLst></p:cTn></p:par></p:tnLst>'
            f'<p:bldLst>{bld}</p:bldLst></p:timing>')


# ───────────────────────── classpoint ─────────────────────────
STRLIST = 'System.Collections.Generic.List`1[[System.String, mscorlib]], mscorlib'
BUTTON = {'multiple_choice': 'btn-multiple-choice.png', 'short_answer': 'btn-short-answer.png', 'word_cloud': 'btn-word-cloud.png', 'image_upload': 'btn-image-upload.png'}
BW, BH = 2222048, 581015


def activity(m):
    base = lambda name, t, ab: {'$type': 'ClassPoint2.Core.Model.Activity, ClassPoint2.Core', 'ActivityId': None, 'Name': name, 'ActivityType': t, 'Width': 0.0, 'Height': 0.0, 'Graphics': None, 'ActivityBase': ab, 'IsLocked': False, 'IsMappedFromCp1': False, 'IsQuizMode': False}
    common = {'activityId': None, 'countdown': m.get('countdown', 0), 'StartWithSlide': False, 'CanMinimize': False, 'CanCountDown': False}
    if m['type'] == 'word_cloud':
        return base('WordCloud', 2, {'$type': 'ClassPoint2.Core.DTO.Activities.WordCloudActivity, ClassPoint2.Core', 'numOfSubmissionsAllowed': m.get('submissions', 5), 'activityType': 'Word Cloud', **common})
    if m['type'] == 'image_upload':
        # Shape read back from a deck where the add-in inserted the button itself (Sept 2026):
        # ActivityType 4; the model carries no ActivityId / IsLocked keys.
        return {'$type': 'ClassPoint2.Core.Model.Activity, ClassPoint2.Core', 'Name': 'ImageUpload', 'ActivityType': 4, 'Width': 0.0, 'Height': 0.0, 'Graphics': None,
                'ActivityBase': {'$type': 'ClassPoint2.Core.DTO.Activities.ImageUploadActivity, ClassPoint2.Core', 'isMultipleSubmissionsAllowed': m.get('multiple', False),
                                 'isNamesHidden': m.get('hide_names', False), 'isCaptionRequired': m.get('caption_required', False), 'activityType': 'Image Upload', **common},
                'IsMappedFromCp1': False, 'IsQuizMode': False}
    if m['type'] == 'short_answer':
        return base('ShortAnswers', 1, {'$type': 'ClassPoint2.Core.DTO.Activities.ShortAnswerActivity, ClassPoint2.Core', 'isMultipleSubmissionsAllowed': m.get('multiple', False), 'isNamesHidden': m.get('hide_names', False), 'gradingInstructions': None, 'activityType': 'Short Answer', **common})
    return base('MultipleChoice', 0, {'$type': 'ClassPoint2.Core.DTO.Activities.MultipleChoiceActivity, ClassPoint2.Core', 'mcChoices': {'$type': STRLIST, '$values': m['choices']}, 'mcIsAllowSelectMultiple': m.get('select_multiple', False), 'mcCorrectAnswers': {'$type': STRLIST, '$values': []}, 'isQuizMode': False, 'correctPoints': 0, 'correctSpeedBonus': None, 'HasCorrectAnswers': False, 'activityType': 'Multiple Choice', **common})


# ───────────────────────── build ─────────────────────────
def build(src: Path, footer: str, activities: Path, out: Path | None = None) -> Path:
    """Add the ait4x master, static font names, entrance animations and the ClassPoint
    buttons to an exported deck. `activities` is the manifest build_pptx() writes."""
    out = out or src.with_name(src.stem + '-classpoint.pptx')
    with zipfile.ZipFile(src) as z:
        parts = {n: z.read(n) for n in z.namelist()}
    T = lambda n: parts[n].decode('utf-8')
    S = lambda n, s: parts.__setitem__(n, s.encode('utf-8') if isinstance(s, str) else s)

    sz = re.search(r'<p:sldSz cx="(\d+)" cy="(\d+)"', T('ppt/presentation.xml'))
    W, H = int(sz.group(1)), int(sz.group(2))
    ct = T('[Content_Types].xml')

    # theme / master / layouts (the export's blank layout stays as layout 1)
    LAYOUTS = layouts(footer)
    ct = install_master(parts, ct, footer)

    # classpoint buttons + tags
    manifest = {int(k): v for k, v in json.loads(Path(activities).read_text()).items() if not k.startswith('_')}
    n = 0
    skipped, used = [], set()
    for no, m in sorted(manifest.items()):
        model = activity(m)
        if model is None:
            skipped.append(no)
            continue
        n += 1
        used.add(BUTTON[m['type']])
        rn, sn = f'ppt/slides/_rels/slide{no}.xml.rels', f'ppt/slides/slide{no}.xml'
        rels = T(rn)
        mx = max(int(x) for x in re.findall(r'Id="rId(\d+)"', rels))
        r_img, r_tag = f'rId{mx+1}', f'rId{mx+2}'
        S(rn, rels.replace('</Relationships>', f'<Relationship Id="{r_img}" Type="{RT}image" Target="../media/{BUTTON[m["type"]]}"/><Relationship Id="{r_tag}" Type="{RT}tags" Target="../tags/tag{n}.xml"/></Relationships>'))
        xml = T(sn)
        sid = max(int(x) for x in re.findall(r'<p:cNvPr id="(\d+)"', xml)) + 1
        pic = (f'<p:pic><p:nvPicPr><p:cNvPr id="{sid}" name="btnInknoeActivityCp2"/><p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr><p:nvPr><p:custDataLst><p:tags r:id="{r_tag}"/></p:custDataLst></p:nvPr></p:nvPicPr>'
               f'<p:blipFill><a:blip r:embed="{r_img}"/><a:stretch><a:fillRect/></a:stretch></p:blipFill><p:spPr><a:xfrm><a:off x="{W - 120*PX - BW}" y="{H - 80*PX - BH}"/><a:ext cx="{BW}" cy="{BH}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>')
        S(sn, xml.replace('</p:spTree>', pic + '</p:spTree>'))
        val = html.escape(json.dumps(model, separators=(',', ':')), quote=True)
        S(f'ppt/tags/tag{n}.xml', f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n<p:tagLst {NS}><p:tag name="ACTIVITYMODEL" val="{val}"/></p:tagLst>')
        ct = ct.replace('</Types>', f'<Override PartName="/ppt/tags/tag{n}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.tags+xml"/></Types>')
    for f in sorted(used):  # only the button artwork that is referenced
        S(f'ppt/media/{f}', (ASSETS / f).read_bytes())
    S('[Content_Types].xml', ct)

    # fonts + animation on every slide
    animated = 0
    for name in [n for n in parts if re.match(r'ppt/slides/slide\d+\.xml$', n)]:
        xml = fix_fonts(re.sub(r'<p:timing>.*?</p:timing>', '', T(name), flags=re.S))
        bs = bands(shapes(xml), W, H)
        if bs:
            xml = xml.replace('</p:sld>', timing(bs) + '</p:sld>'); animated += 1
        S(name, xml)

    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for n, d in parts.items():
            z.writestr(n, d)
    print(f'wrote {out}: {len(LAYOUTS)} layouts, {animated} animated slides, {len(manifest) - len(skipped)} ClassPoint activities')
    for no, m in sorted(manifest.items()):
        print(f'  slide {no:>2}: {m["type"]}' + ('  (NO BUTTON: add it by hand in ClassPoint)' if no in skipped else ''))
    if skipped:
        print(f'WARNING: slides {skipped}: activity type without a ClassPoint model — insert the button by hand in PowerPoint (ClassPoint tab) and save')
    return out


def template(out: Path, footer: str) -> Path:
    """Write a standalone .potx: ait4x theme, master, all layouts, one sample slide per layout."""
    RELS = 'http://schemas.openxmlformats.org/package/2006/relationships'
    parts = {}
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.template.main+xml"/>'
          '<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>'
          '<Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/></Types>')
    LAYOUTS = layouts(footer)
    ct = install_master(parts, ct, footer, first_layout=1)
    sld_ids, sld_rels = '', ''
    for i, (name, bg, logo, xml) in enumerate(LAYOUTS, start=1):
        phs = re.findall(r'<p:sp>.*?</p:sp>', xml, re.S)
        sps = ''
        for s in phs:
            m = re.search(r'<p:cNvPr id="(\d+)" name="([^"]*)"/>.*?<p:ph([^/]*)/>', s, re.S)
            if not m or 'type="ftr"' in m.group(3) or 'type="sldNum"' in m.group(3):
                continue
            sps += (f'<p:sp><p:nvSpPr><p:cNvPr id="{m.group(1)}" name="{m.group(2)}"/><p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr><p:nvPr><p:ph{m.group(3)}/></p:nvPr></p:nvSpPr>'
                    '<p:spPr/><p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:endParaRPr lang="en-US"/></a:p></p:txBody></p:sp>')
        parts[f'ppt/slides/slide{i}.xml'] = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<p:sld {NS}><p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
            f'<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>{sps}</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>').encode()
        parts[f'ppt/slides/_rels/slide{i}.xml.rels'] = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="{RELS}"><Relationship Id="rId1" Type="{RT}slideLayout" Target="../slideLayouts/slideLayout{i}.xml"/></Relationships>').encode()
        ct = ct.replace('</Types>', f'<Override PartName="/ppt/slides/slide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/></Types>')
        sld_ids += f'<p:sldId id="{256 + i}" r:id="rId{2 + i}"/>'
        sld_rels += f'<Relationship Id="rId{2 + i}" Type="{RT}slide" Target="slides/slide{i}.xml"/>'
    parts['ppt/presentation.xml'] = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<p:presentation {NS} saveSubsetFonts="1">'
        f'<p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst><p:sldIdLst>{sld_ids}</p:sldIdLst>'
        f'<p:sldSz cx="{1920 * PX}" cy="{1080 * PX}"/><p:notesSz cx="6858000" cy="9144000"/></p:presentation>').encode()
    parts['ppt/_rels/presentation.xml.rels'] = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="{RELS}"><Relationship Id="rId1" Type="{RT}slideMaster" Target="slideMasters/slideMaster1.xml"/>'
        f'<Relationship Id="rId2" Type="{RT}theme" Target="theme/theme1.xml"/>{sld_rels}</Relationships>').encode()
    parts['_rels/.rels'] = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="{RELS}"><Relationship Id="rId1" Type="{RT}officeDocument" Target="ppt/presentation.xml"/></Relationships>').encode()
    parts['[Content_Types].xml'] = ct.encode()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for n, d in parts.items():
            z.writestr(n, d)
    print(f'wrote {out}: {len(LAYOUTS)} layouts')
    return out
