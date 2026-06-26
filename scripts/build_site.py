#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import json, re, html

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'

SIDE_STYLE = ".side-track{margin:46px 0 0 auto;max-width:760px;border:1px dashed rgba(213,200,186,.95);border-radius:22px;background:rgba(255,255,255,.44);padding:12px 16px;color:var(--muted)}.side-track summary{cursor:pointer;display:flex;justify-content:space-between;align-items:center;gap:16px;font-size:13px;font-weight:900;color:#6a5d52}.side-track[open]{max-width:none;padding:20px;border-style:solid;background:rgba(255,255,255,.65)}.side-track .side-note{margin:10px 0 18px;font-size:13px}.side-count{font-family:Georgia,serif;color:#9b6b25}"

INDEX = f'''<!doctype html>
<html lang="en" data-page="index">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Acoustic–Optics Imaging Research Atlas</title>
  <meta name="description" content="A bilingual research atlas for acoustic-optical imaging, acoustic coded imaging, sonar reconstruction, acoustic holography, photoacoustic imaging, and acousto-optic imaging.">
  <link rel="stylesheet" href="style.css"><style>{SIDE_STYLE}</style>
</head>
<body data-page="index"><div class="grain"></div><div class="shell"><header class="topbar"><a class="brand" href="index.html" aria-label="Acoustic–Optics Imaging home"><span class="mark">AΩ</span><span>Acoustic–Optics Imaging</span></a><nav class="nav"><a href="#atlas" data-i18n="navAtlas">Atlas</a><a href="#timeline" data-i18n="navTimeline">Timeline</a><a href="#library" data-i18n="navLibrary">Library</a><a href="updates.html" data-i18n="navUpdates">Auto updates</a></nav><div class="lang" aria-label="Language switch"><button data-lang="en">EN</button><button data-lang="zh">中文</button></div></header><main><section class="hero editorial" id="atlas"><div class="hero-copy"><p class="eyebrow" data-i18n="eyebrow">Curated research atlas</p><h1 data-i18n="heroTitle">A living map of sound, light, and computational imaging.</h1><p class="lead" data-i18n="heroSubtitle">A selective, auto-audited guide to acoustic-optical fusion, coded acoustics, sonar reconstruction, acoustic holography, photoacoustic imaging, and acousto-optic imaging across top venues.</p><div class="actions"><a class="primary" href="#library" data-i18n="browseLibrary">Browse library</a><a class="secondary" href="updates.html" data-i18n="viewUpdates">View auto updates</a></div></div><aside class="hero-panel"><div class="metric"><b id="m-papers">—</b><span data-i18n="metricPapers">curated papers</span></div><div class="metric"><b id="m-years">—</b><span data-i18n="metricYears">year span</span></div><div class="metric"><b id="m-venues">—</b><span data-i18n="metricVenues">venue groups</span></div><div class="signal"><span data-i18n="signalTitle">Update policy</span><p data-i18n="signalText">Every run resolves final journal or conference venues when arXiv papers have accepted versions.</p></div></aside></section><section class="section-head spacious"><div><p class="eyebrow small" data-i18n="roadmapEyebrow">Reading roadmap</p><h2 data-i18n="roadmapTitle">How the field is evolving</h2><p data-i18n="roadmapSubtitle">The papers are organized as research threads rather than a flat bibliography.</p></div></section><section id="roadmap" class="roadmap"></section><section class="section-head spacious" id="timeline"><div><p class="eyebrow small" data-i18n="timelineEyebrow">Chronology</p><h2 data-i18n="timelineTitle">Development timeline</h2><p data-i18n="timelineSubtitle">Click a year to filter the library and inspect how the emphasis shifts over time.</p></div><button id="clearYear" class="ghost" data-i18n="clearYear">Show all years</button></section><section id="yearline" class="yearline"></section><section class="section-head spacious"><div><p class="eyebrow small" data-i18n="themeEyebrow">Topic structure</p><h2 data-i18n="themeTitle">Topic map</h2><p data-i18n="themeSubtitle">A compact overview of recurring technical directions.</p></div></section><section id="topicMap" class="topic-map"></section><section id="library" class="library-shell"><section class="section-head"><div><p class="eyebrow small" data-i18n="libraryEyebrow">Curated library</p><h2 data-i18n="libraryTitle">Verified papers</h2><p data-i18n="librarySubtitle">Filter by year, venue, topic, and relevance. Chinese mode provides natural Chinese titles and reading notes.</p></div><p id="count" class="count">—</p></section><section class="toolbar advanced"><input id="q" type="search"><select id="year"></select><select id="venue"></select><select id="topic"></select><select id="rel"></select></section><section id="grid" class="grid refined"></section></section><details id="mmwave" class="side-track"><summary><span data-i18n="mmwaveCollapsedTitle">Optional side track: Millimeter-Wave Radar Imaging</span><span id="mmwaveCount" class="side-count">—</span></summary><p class="side-note" data-i18n="mmwaveCollapsedSubtitle">A small, collapsed appendix for recent mmWave radar imaging and radar point-cloud papers.</p><section id="mmwaveGrid" class="grid refined"></section></details></main><footer class="footer"><p data-i18n="footerPdf">PDF links point only to open or legitimate sources.</p><p data-i18n="footerPrivacy">Public metadata uses neutral project language and avoids private research-context notes.</p></footer></div><script src="script.js" defer></script></body></html>
'''

UPDATES = '''<!doctype html><html lang='en' data-page='updates'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>Auto-reviewed Updates · Acoustic–Optics Imaging</title><link rel='stylesheet' href='style.css'></head><body data-page='updates'><div class='grain'></div><div class='shell'><header class='topbar'><a class='brand' href='index.html'><span class='mark'>AΩ</span><span>Acoustic–Optics Imaging</span></a><nav class='nav'><a href='index.html' data-i18n='navLibrary'>Library</a><a href='updates.html' data-i18n='navUpdates'>Auto updates</a><a href='data/papers.json'>papers.json</a><a href='data/candidates.json'>candidates.json</a></nav><div class='lang'><button data-lang='en'>EN</button><button data-lang='zh'>中文</button></div></header><main><section class='hero editorial'><div><p class='eyebrow' data-i18n='updatesEyebrow'>Automated discovery</p><h1 data-i18n='updatesTitle'>Auto-reviewed paper updates.</h1><p class='lead' data-i18n='updatesSubtitle'>The scheduled workflow searches public scholarly sources every 6 hours. A curation agent scores venue quality, source reliability, topical relevance, PDF availability, and duplicate status.</p></div><aside class='hero-panel'><div class='metric'><b id='m-candidates'>—</b><span data-i18n='metricCandidates'>auto-reviewed candidates</span></div><div class='metric'><b id='m-promoted'>—</b><span data-i18n='metricPromoted'>agent-promoted papers</span></div><div class='metric'><b id='m-latest'>—</b><span data-i18n='metricLatest'>latest update</span></div></aside></section><section class='toolbar one'><input id='q' type='search'></section><section class='section-head'><div><h2 data-i18n='candidateTitle'>Candidate stream</h2><p data-i18n='candidateSubtitle'>Each item keeps its audit status, score, and source.</p></div><p id='count' class='count'>—</p></section><section id='grid' class='grid'></section></main><footer class='footer'><p>Raw JSON: <a href='data/candidates.json'>data/candidates.json</a> · Run log: <a href='data/last_update.json'>data/last_update.json</a></p></footer></div><script src='script.js' defer></script></body></html>'''

PAPER = '''<!doctype html><html lang='en' data-page='paper'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>Paper details · Acoustic–Optics Imaging</title><link rel='stylesheet' href='style.css'></head><body data-page='paper'><div class='grain'></div><div class='shell'><header class='topbar'><a class='brand' href='index.html'><span class='mark'>AΩ</span><span>Acoustic–Optics Imaging</span></a><nav class='nav'><a href='index.html' data-i18n='backToIndex'>← Back to paper index</a><a href='updates.html' data-i18n='navUpdates'>Auto updates</a><a href='data/papers.json'>papers.json</a></nav><div class='lang'><button data-lang='en'>EN</button><button data-lang='zh'>中文</button></div></header><main><p class='back'><a href='index.html' data-i18n='backToIndex'>← Back to paper index</a></p><article id='detail' class='detail'></article></main><footer class='footer'><p data-i18n='footerPrivacy'>Public metadata uses neutral project language.</p></footer></div><script src='script.js' defer></script></body></html>'''

def load(name, default):
    p = DATA / name
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else default

def write_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def sanitize(txt):
    txt = str(txt or '')
    scope = chr(0x4E0E) + chr(0x4F60) + chr(0x7684)
    poss = chr(0x4F60) + chr(0x7684)
    txt = re.sub(re.escape(scope) + r'[“\"][^。]*[”\"][^。]*。?', '该论文与公开追踪主题直接相关，并提供可核验来源。', txt)
    return txt.replace(poss, '该')

def redirect(pid, title):
    pid = html.escape(pid); title = html.escape(title or pid)
    return f"""<!doctype html><html lang='en'><head><meta charset='utf-8'><meta http-equiv='refresh' content='0; url=../paper.html?id={pid}'><meta name='viewport' content='width=device-width, initial-scale=1'><title>{title} · Acoustic–Optics Imaging</title><link rel='canonical' href='../paper.html?id={pid}'><link rel='stylesheet' href='../style.css'></head><body><main class='shell'><p class='note'>This page has moved to <a href='../paper.html?id={pid}'>paper.html?id={pid}</a>.</p></main></body></html>"""

def main():
    papers = load('papers.json', [])
    focus = load('focus_papers.json', [])
    mmwave = load('mmwave_papers.json', [])
    changed = False
    for collection in [papers, focus, mmwave]:
        for p in collection:
            for k, v in list(p.items()):
                if isinstance(v, str):
                    nv = sanitize(v)
                    if nv != v:
                        p[k] = nv; changed = True
    if changed:
        write_json(DATA / 'papers.json', papers)
        write_json(DATA / 'focus_papers.json', focus)
        write_json(DATA / 'mmwave_papers.json', mmwave)
    (ROOT / 'index.html').write_text(INDEX, encoding='utf-8')
    (ROOT / 'updates.html').write_text(UPDATES, encoding='utf-8')
    (ROOT / 'paper.html').write_text(PAPER, encoding='utf-8')
    d = ROOT / 'papers'; d.mkdir(exist_ok=True)
    for p in papers + focus + mmwave:
        if p.get('id'):
            (d / f"{p['id']}.html").write_text(redirect(p['id'], p.get('title', '')), encoding='utf-8')
    print(f'Rebuilt research-atlas site for {len(papers)} papers, {len(focus)} focus papers, {len(mmwave)} side-track papers')

if __name__ == '__main__':
    main()
