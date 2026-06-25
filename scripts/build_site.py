#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import json, html

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'


def esc(x):
    return html.escape(str(x or ''))


def link(url, label):
    return f'<a href="{esc(url)}" target="_blank" rel="noopener">{esc(label)}</a>' if url else ''


def load(name, default):
    p = DATA / name
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else default


def bibtex(p):
    key = p['id'].replace('-', '')[:40]
    typ = 'article' if p.get('venue_type', '').startswith('journal') else 'inproceedings'
    fields = {
        'title': p.get('title', ''),
        'author': p.get('authors', '').replace(';', ' and '),
        'year': p.get('year', ''),
        ('journal' if typ == 'article' else 'booktitle'): p.get('venue', ''),
    }
    if p.get('doi'):
        fields['doi'] = p['doi']
    if p.get('primary_url'):
        fields['url'] = p['primary_url']
    out = [f'@{typ}' + '{' + key + ',']
    out += [f'  {k} = {{{v}}},' for k, v in fields.items() if v]
    out += ['}']
    return '\n'.join(out)


papers = load('papers.json', [])
papers = sorted(papers, key=lambda p: (p.get('publication_date') or str(p.get('year', '')), p.get('year', 0)), reverse=True)
candidates = load('candidates.json', [])
candidates = sorted(candidates, key=lambda p: (p.get('score', 0), p.get('publication_date', ''), p.get('last_seen', '')), reverse=True)
last_update = load('last_update.json', {})

venues = sorted({p.get('venue_group', '') for p in papers if p.get('venue_group')})
topics = sorted({t for p in papers for t in p.get('topics', [])})
(ROOT / 'papers').mkdir(exist_ok=True)

nav = '<nav class="nav"><a href="index.html">Verified papers</a><a href="updates.html">Auto candidates</a><a href="data/papers.json">papers.json</a><a href="data/candidates.json">candidates.json</a></nav>'

cards = []
for p in papers:
    cls = 'core' if p.get('relevance') == 'core' else 'related'
    tags = ''.join(f'<span class="tag">{esc(t)}</span>' for t in p.get('topics', []))
    links = [link(f"papers/{p['id']}.html", '详情'), link(p.get('primary_url'), 'Publisher')]
    if p.get('pdf_url'):
        links.append(link(p['pdf_url'], 'PDF'))
    if p.get('project_url'):
        links.append(link(p['project_url'], 'Project'))
    if p.get('code_url'):
        links.append(link(p['code_url'], 'Code'))
    text = (p.get('title','') + ' ' + p.get('authors','') + ' ' + p.get('venue','') + ' ' + ' '.join(p.get('topics', [])) + ' ' + p.get('summary_cn','')).lower()
    cards.append(
        f'<article class="card" data-text="{esc(text)}" data-venue="{esc(p.get("venue_group", ""))}" data-topics="{esc(" ".join(p.get("topics", [])))}" data-rel="{esc(p.get("relevance", ""))}">'
        f'<h2>{esc(p["title"])}</h2><div class="meta">{esc(p.get("authors", ""))}<br>{esc(p.get("venue", ""))} · {esc(p.get("year", ""))} · <span class="badge {cls}">{esc(p.get("relevance", ""))}</span></div>'
        f'<div class="tags">{tags}</div><div class="summary">{esc(p.get("summary_cn", ""))}</div><div class="why">{esc(p.get("why_include_cn", ""))}</div><div class="links">{"".join(links)}</div></article>'
    )

index = f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Acoustic-Optics Imaging Papers</title><link rel="stylesheet" href="style.css"></head><body><main class="wrap">{nav}<section class="hero"><h1>Acoustic-Optics / Acoustic Imaging Paper Tracker</h1><p class="sub">顶级期刊与顶级会议中，声光融合成像、声学编码成像、声学成像、声学全息、声呐/相机融合、光声/声光成像相关论文的人工核验索引。</p><div class="stats"><span class="stat">{len(papers)} verified papers</span><span class="stat">{len(candidates)} auto candidates</span><span class="stat">verified: {esc(papers[0].get('last_verified','')) if papers else ''}</span><span class="stat">last scheduled run: {esc(last_update.get('last_run','not yet'))}</span></div></section><section class="controls"><input id="q" placeholder="搜索标题、作者、venue、topic..."><select id="venue"><option value="">全部 venue group</option>{''.join(f'<option>{esc(v)}</option>' for v in venues)}</select><select id="topic"><option value="">全部 topic</option>{''.join(f'<option>{esc(t)}</option>' for t in topics)}</select><select id="rel"><option value="">全部相关度</option><option value="core">core</option><option value="related">related</option></select></section><section class="grid">{''.join(cards)}</section><section class="footer"><p>PDF links point only to publisher open PDFs, arXiv, PMC, CVF, institutional repositories, or author/preprint pages.</p><p>自动任务每 6 小时更新 <a href="updates.html">candidates</a>；正式 verified library 仍建议人工核验后写入 <code>data/papers.json</code>。</p></section></main><script src="script.js"></script></body></html>'''
(ROOT / 'index.html').write_text(index, encoding='utf-8')

# Candidates / scheduled update page.
cards2 = []
for c in candidates:
    links = [link(c.get('primary_url'), 'Primary')]
    if c.get('pdf_url'):
        links.append(link(c.get('pdf_url'), 'PDF'))
    if c.get('doi'):
        links.append(link('https://doi.org/' + c['doi'], 'DOI'))
    reasons = ''.join(f'<span class="tag">{esc(r)}</span>' for r in c.get('reasons', []))
    text = (c.get('title','') + ' ' + c.get('authors','') + ' ' + c.get('venue','') + ' ' + c.get('matched_query','')).lower()
    cards2.append(
        f'<article class="card candidate" data-text="{esc(text)}" data-venue="" data-topics="" data-rel="candidate">'
        f'<h2>{esc(c.get("title"))}</h2><div class="meta">{esc(c.get("authors"))}<br>{esc(c.get("venue"))} · {esc(c.get("year"))} · score {esc(c.get("score"))} · {esc(c.get("source"))}</div>'
        f'<div class="tags">{reasons}</div><div class="summary">Matched query: <code>{esc(c.get("matched_query"))}</code></div>'
        f'<div class="why">Status: {esc(c.get("status"))}. First seen: {esc(c.get("first_seen"))}; last seen: {esc(c.get("last_seen"))}; times seen: {esc(c.get("times_seen"))}</div><div class="links">{"".join(links)}</div></article>'
    )
updates = f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Auto Candidates · Acoustic-Optics Imaging</title><link rel="stylesheet" href="style.css"></head><body><main class="wrap">{nav}<section class="hero"><h1>Auto-discovered paper candidates</h1><p class="sub">这里是 GitHub Actions 每 6 小时自动检索得到的候选论文。它们还不是正式收录论文；请核验 title、venue、DOI、PDF、贡献相关性后，再手动复制到 <code>data/papers.json</code> 并运行 <code>scripts/build_site.py</code>。</p><div class="stats"><span class="stat">{len(candidates)} candidates</span><span class="stat">last run: {esc(last_update.get('last_run','not yet'))}</span><span class="stat">raw seen: {esc(last_update.get('raw_candidates_seen',''))}</span></div></section><section class="controls one"><input id="q" placeholder="搜索 candidates..."/><select id="venue" hidden><option value=""></option></select><select id="topic" hidden><option value=""></option></select><select id="rel" hidden><option value=""></option></select></section><section class="grid">{''.join(cards2) if cards2 else '<p class="note">No candidates yet. Run <code>python scripts/update_candidates.py</code> or wait for the scheduled workflow.</p>'}</section><section class="footer"><p>Raw JSON: <a href="data/candidates.json">data/candidates.json</a> · Run log: <a href="data/last_update.json">data/last_update.json</a></p></section></main><script src="script.js"></script></body></html>'''
(ROOT / 'updates.html').write_text(updates, encoding='utf-8')

for p in papers:
    tags = ''.join(f'<span class="tag">{esc(t)}</span>' for t in p.get('topics', []))
    sources = ''.join(f'<li>{link(s, s)}</li>' for s in p.get('sources', []))
    html_doc = f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(p['title'])}</title><link rel="stylesheet" href="../style.css"></head><body><main class="wrap paper"><p><a href="../index.html">← Back to index</a></p><h1>{esc(p['title'])}</h1><div class="meta">{esc(p.get('authors',''))}</div><div class="tags">{tags}</div><div class="kv"><div>Venue</div><div>{esc(p.get('venue',''))}</div><div>Year / Date</div><div>{esc(p.get('year',''))} / {esc(p.get('publication_date',''))}</div><div>Venue group</div><div>{esc(p.get('venue_group',''))}</div><div>DOI</div><div>{link('https://doi.org/'+p['doi'],p['doi']) if p.get('doi') else 'N/A'}</div><div>Publisher</div><div>{link(p.get('primary_url'), p.get('primary_url'))}</div><div>PDF</div><div>{link(p.get('pdf_url'), p.get('pdf_url')) if p.get('pdf_url') else 'N/A'}</div><div>Project</div><div>{link(p.get('project_url'), p.get('project_url')) if p.get('project_url') else 'N/A'}</div><div>Code</div><div>{link(p.get('code_url'), p.get('code_url')) if p.get('code_url') else 'N/A'}</div><div>Relevance</div><div>{esc(p.get('relevance',''))}</div><div>Last verified</div><div>{esc(p.get('last_verified',''))}</div></div><h2>中文摘要</h2><p>{esc(p.get('summary_cn',''))}</p><h2>为什么收录</h2><p>{esc(p.get('why_include_cn',''))}</p><h2>PDF / 下载说明</h2><p class="note">{esc(p.get('download_note',''))}</p><h2>核验来源</h2><ul>{sources}</ul><h2>BibTeX</h2><pre>{esc(bibtex(p))}</pre></main></body></html>'''
    (ROOT / 'papers' / f"{p['id']}.html").write_text(html_doc, encoding='utf-8')

print(f'Rebuilt {len(papers)} verified papers and {len(candidates)} candidates')
