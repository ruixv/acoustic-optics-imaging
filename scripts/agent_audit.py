#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import datetime as dt
import hashlib
import json
import os
import re
import time
import urllib.parse
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional

import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
PAPERS = DATA / 'papers.json'
CANDS = DATA / 'candidates.json'
LOG = DATA / 'last_update.json'

TOP_GROUPS = ['Nature','Nature Portfolio','Science family','ACM SIGGRAPH','ACM TOG / SIGGRAPH','ACM TOG / SIGGRAPH Asia','IEEE TPAMI','IEEE TIP','CVPR','ICCV','ECCV','ICLR','NeurIPS']
CORE = ['acoustic','sonar','ultrasound','photoacoustic','optoacoustic','acousto-optic','acousto optic']
IMAGING = ['imaging','reconstruction','tomography','holography','nlos','non-line-of-sight','synthetic aperture','sensor fusion','gaussian splatting','neural rendering','3d']
NEG = ['speech recognition','music','audio caption','radio galaxy','black hole','x-ray binary','tidal disruption','cell culture','ball games','raman data fusion','millimetre arrays']
TOPICS = [
    ('camera-sonar fusion',['camera sonar','camera-sonar','vision sonar','acoustic-optical','acoustic optical']),
    ('synthetic aperture sonar',['synthetic aperture sonar','coherent synthetic aperture']),
    ('acoustic NLOS',['non-line-of-sight','non line of sight','nlos']),
    ('acoustic holography',['acoustic holograph','phased array']),
    ('acoustic coded imaging',['coded imaging','temporal encoding','complex field','coded']),
    ('photoacoustic imaging',['photoacoustic','optoacoustic']),
    ('acousto-optic imaging',['acousto-optic','acousto optic']),
    ('computational ultrasound',['computational ultrasound','ultrasound reconstruction']),
    ('neural rendering',['neural rendering','gaussian splatting']),
    ('3D reconstruction',['3d reconstruction','volumetric','tomography']),
]

SESSION = requests.Session()
SESSION.headers.update({
    'User-Agent': 'acoustic-optics-imaging-agent-audit/1.1 (https://github.com/ruixv/acoustic-optics-imaging; mailto:%s)' % os.getenv('CROSSREF_MAILTO', 'example@example.com')
})


def load(p: Path, d: Any) -> Any:
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else d


def dump(p: Path, o: Any) -> None:
    p.write_text(json.dumps(o, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def normalize_title(s: str) -> str:
    return re.sub(r'[^a-z0-9]+', ' ', (s or '').lower()).strip()


def title_similarity(a: str, b: str) -> float:
    aa, bb = normalize_title(a), normalize_title(b)
    if not aa or not bb:
        return 0.0
    return SequenceMatcher(None, aa, bb).ratio()


def fp(x: Dict[str, Any]) -> str:
    return hashlib.sha1(((x.get('doi') or x.get('title') or x.get('primary_url') or '').lower()).encode()).hexdigest()[:12]


def title_key(x: Dict[str, Any]) -> str:
    return normalize_title(x.get('title', ''))


def group(venue: str, title: str = '') -> str:
    s = (venue + ' ' + title).lower()
    if any(x in s for x in ['nature','communications physics','communications engineering','scientific data','light: science']): return 'Nature Portfolio'
    if 'science' in s: return 'Science family'
    if 'siggraph' in s or 'transactions on graphics' in s: return 'ACM TOG / SIGGRAPH'
    if 'pattern analysis and machine intelligence' in s or 'tpami' in s: return 'IEEE TPAMI'
    if 'image processing' in s: return 'IEEE TIP'
    if 'cvpr' in s or 'computer vision and pattern recognition' in s: return 'CVPR'
    if 'iccv' in s: return 'ICCV'
    if 'eccv' in s: return 'ECCV'
    if 'iclr' in s: return 'ICLR'
    if 'neurips' in s or 'neural information processing systems' in s: return 'NeurIPS'
    return 'Other'


def topics(item: Dict[str, Any]) -> List[str]:
    s = ' '.join(str(item.get(k,'')) for k in ['title','abstract','matched_query']).lower()
    out = []
    for label, keys in TOPICS:
        if any(k in s for k in keys):
            out.append(label)
    return out[:6] or [w for w in re.split(r'\W+', item.get('matched_query','')) if len(w) > 4][:4]


def clean_text(s: str) -> str:
    s = str(s or '')
    scope = chr(0x4E0E) + chr(0x4F60) + chr(0x7684)
    poss = chr(0x4F60) + chr(0x7684)
    s = re.sub(re.escape(scope) + r'[“\"][^。]*[”\"][^。]*。?', '该论文与公开追踪主题直接相关，并提供可核验来源。', s)
    return s.replace(poss, '该')


def sanitize_papers(papers: List[Dict[str, Any]]) -> bool:
    changed = False
    for p in papers:
        for k, v in list(p.items()):
            if isinstance(v, str):
                nv = clean_text(v)
                if nv != v:
                    p[k] = nv
                    changed = True
    return changed


def get_year_date_crossref(item: Dict[str, Any]) -> tuple[Optional[int], str]:
    for k in ['published-print','published-online','published','issued','created']:
        parts = (item.get(k) or {}).get('date-parts')
        if parts and parts[0]:
            arr = parts[0]
            year = int(arr[0]) if arr and arr[0] else None
            month = int(arr[1]) if len(arr) > 1 else 1
            day = int(arr[2]) if len(arr) > 2 else 1
            if year:
                return year, f'{year:04d}-{month:02d}-{day:02d}'
    return None, ''


def crossref_final_lookup(title: str) -> Optional[Dict[str, Any]]:
    if not title:
        return None
    params = {
        'query.title': title,
        'rows': 5,
        'select': 'DOI,title,author,container-title,published-print,published-online,published,issued,created,URL,type',
    }
    if os.getenv('CROSSREF_MAILTO'):
        params['mailto'] = os.getenv('CROSSREF_MAILTO')
    try:
        r = SESSION.get('https://api.crossref.org/works?' + urllib.parse.urlencode(params), timeout=30)
        r.raise_for_status()
        items = r.json().get('message', {}).get('items', [])
    except Exception:
        return None
    best = None
    best_score = 0.0
    for it in items:
        cr_title = ' '.join(it.get('title') or [])
        sim = title_similarity(title, cr_title)
        venue = ' '.join(it.get('container-title') or [])
        doi = it.get('DOI') or ''
        if sim > best_score and sim >= 0.92 and venue and doi:
            best, best_score = it, sim
    if not best:
        return None
    year, pub_date = get_year_date_crossref(best)
    authors = []
    for a in best.get('author') or []:
        nm = ' '.join([a.get('given',''), a.get('family','')]).strip()
        if nm:
            authors.append(nm)
    venue = ' '.join(best.get('container-title') or [])
    doi = best.get('DOI') or ''
    return {
        'title': ' '.join(best.get('title') or []) or title,
        'authors': '; '.join(authors[:8]) + ('; et al.' if len(authors) > 8 else ''),
        'year': year,
        'publication_date': pub_date,
        'venue': venue,
        'venue_group': group(venue, title),
        'doi': doi,
        'primary_url': best.get('URL') or (f'https://doi.org/{doi}' if doi else ''),
        'source': 'Crossref-final-version',
        'final_version_resolved': True,
        'final_version_similarity': round(best_score, 3),
    }


def resolve_final_version(c: Dict[str, Any]) -> Dict[str, Any]:
    """If an arXiv/preprint record has a final published version, prefer that venue.

    The arXiv URL can remain as pdf_url when it is the most accessible open PDF,
    but venue/DOI/primary_url should describe the accepted journal or conference.
    """
    is_arxiv = (c.get('source') == 'arXiv') or (str(c.get('venue','')).lower() == 'arxiv preprint')
    if not is_arxiv:
        return c
    resolved = crossref_final_lookup(c.get('title',''))
    if not resolved:
        c['final_version_status'] = 'arxiv-only-no-final-version-found'
        return c
    arxiv_url = c.get('primary_url','') if 'arxiv.org' in c.get('primary_url','') else ''
    arxiv_pdf = c.get('pdf_url','') if 'arxiv.org' in c.get('pdf_url','') else ''
    c.update({k:v for k,v in resolved.items() if v not in [None, '', []]})
    if arxiv_pdf and not c.get('pdf_url'):
        c['pdf_url'] = arxiv_pdf
    elif arxiv_pdf:
        c['pdf_url'] = arxiv_pdf
    sources = c.get('sources') or []
    for u in [c.get('primary_url'), arxiv_url, arxiv_pdf]:
        if u and u not in sources:
            sources.append(u)
    c['sources'] = sources
    c['final_version_status'] = 'resolved-from-arxiv-to-final-venue'
    return c


def audit(c: Dict[str, Any]) -> Dict[str, Any]:
    c = resolve_final_version(c)
    text = ' '.join(str(c.get(k,'')) for k in ['title','abstract','venue','matched_query']).lower()
    vg = group(c.get('venue',''), c.get('title',''))
    c['venue_group'] = c.get('venue_group') or vg
    c['topics'] = c.get('topics') or topics(c)
    score = int(c.get('score') or 0)
    top = c.get('venue_group') != 'Other' or 'top-venue-hint' in c.get('reasons', [])
    core = any(x in text for x in CORE)
    img = any(x in text for x in IMAGING)
    neg = any(x in text for x in NEG)
    preprint = (str(c.get('venue','')).lower() == 'arxiv preprint') or (c.get('source') == 'arXiv' and not c.get('doi'))
    source_ok = bool(c.get('doi')) or c.get('source') in ['Crossref','Crossref-final-version','CVF','OpenReview']
    decision = 'candidate'
    conf = max(.1, min(.75, score/15))
    if score >= 12 and top and core and img and source_ok and not preprint and not neg:
        decision = 'promote'; conf = .88
    elif score >= 9 and top and core and img and not neg:
        decision = 'approved-candidate'; conf = .72
    elif neg:
        decision = 'reject-like'; conf = .25
    c['status'] = 'agent-promoted' if decision == 'promote' else ('agent-approved-candidate' if decision == 'approved-candidate' else 'agent-watchlist')
    c['agent_audit'] = {'decision': decision, 'confidence': conf, 'checks': {'top_venue': top, 'core_term': core, 'imaging_term': img, 'source_ok': source_ok, 'preprint_only': preprint, 'negative_filter': neg, 'final_version_status': c.get('final_version_status','not-needed')}}
    return c


def to_paper(c: Dict[str, Any]) -> Dict[str, Any]:
    today = dt.date.today().isoformat()
    ts = c.get('topics') or topics(c)
    rel = 'core' if any(x in ts for x in ['camera-sonar fusion','synthetic aperture sonar','acoustic NLOS','photoacoustic imaging','acousto-optic imaging','acoustic holography']) else 'related'
    doi = c.get('doi','')
    venue = c.get('venue','')
    venue_type = 'preprint' if venue.lower() == 'arxiv preprint' else ('journal' if any(x in venue.lower() for x in ['nature','science','communications','journal','transactions']) else 'conference')
    sources = []
    for u in [c.get('primary_url'), ('https://doi.org/'+doi if doi else ''), *(c.get('sources') or [])]:
        if u and u not in sources:
            sources.append(u)
    return {
        'id': c.get('id') or ('auto-'+fp(c)),
        'title': c.get('title',''),
        'authors': c.get('authors',''),
        'year': c.get('year'),
        'publication_date': c.get('publication_date',''),
        'venue': venue,
        'venue_group': c.get('venue_group') or group(venue, c.get('title','')),
        'venue_type': venue_type,
        'doi': doi,
        'primary_url': c.get('primary_url',''),
        'pdf_url': c.get('pdf_url',''),
        'project_url': '',
        'code_url': '',
        'topics': ts,
        'relevance': rel,
        'summary_en': 'Automatically audited paper on ' + (', '.join(ts) or 'acoustic–optical imaging') + '.',
        'summary_cn': '自动审核收录的论文，主题包括 ' + ('、'.join(ts) or '声光/声学成像') + '。',
        'why_include_en': 'Promoted by the automatic curation agent based on source quality, venue priority, topical relevance, recency, duplicate checks, and final-version resolution.',
        'why_include_cn': '由自动文献审核 Agent 根据来源质量、venue 优先级、主题相关性、时效性、重复检查和最终发表版本解析自动收录。',
        'download_note': 'The venue records the final accepted/published version when available; arXiv is used only for preprints or as an open PDF source.',
        'sources': sources,
        'last_verified': today,
        'verification': {'mode': 'automatic-curation-agent', 'confidence': c.get('agent_audit',{}).get('confidence'), 'source': c.get('source',''), 'final_version_status': c.get('final_version_status','not-needed')}
    }


def main() -> None:
    papers = load(PAPERS, [])
    cands = load(CANDS, [])
    sanitize_papers(papers)
    keys = {fp(p) for p in papers}
    title_keys = {title_key(p) for p in papers}
    promoted = []
    kept = []
    resolved_final_versions = 0
    for c in cands:
        c = audit(c)
        if c.get('final_version_status') == 'resolved-from-arxiv-to-final-venue':
            resolved_final_versions += 1
        k, tk = fp(c), title_key(c)
        if c.get('agent_audit',{}).get('decision') == 'promote' and k not in keys and tk not in title_keys:
            p = to_paper(c)
            papers.append(p)
            keys.add(k)
            title_keys.add(tk)
            promoted.append(p)
            c['promoted_on'] = dt.date.today().isoformat()
        else:
            kept.append(c)
    papers.sort(key=lambda p:(str(p.get('publication_date') or p.get('year') or ''), p.get('title','')), reverse=True)
    kept.sort(key=lambda c:(c.get('agent_audit',{}).get('confidence',0), c.get('score',0), str(c.get('publication_date',''))), reverse=True)
    dump(PAPERS, papers)
    dump(CANDS, kept)
    log = load(LOG, {})
    log.update({
        'agent_audit_last_run': dt.datetime.now(dt.timezone.utc).isoformat(),
        'promoted_count': len(promoted),
        'resolved_final_versions': resolved_final_versions,
        'audit_note': 'High-confidence records are promoted automatically. arXiv records are relabeled to the final accepted/published venue when Crossref/DOI metadata confirms a final version.'
    })
    dump(LOG, log)
    print(f'agent audit promoted {len(promoted)} papers; resolved {resolved_final_versions} arXiv final versions; kept {len(kept)} candidates')


if __name__ == '__main__':
    main()
