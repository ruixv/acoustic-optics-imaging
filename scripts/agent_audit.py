#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import datetime as dt, hashlib, json, os, re, urllib.parse
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional
import requests

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
PAPERS=DATA/'papers.json'
FOCUS=DATA/'focus_papers.json'
CANDS=DATA/'candidates.json'
LOG=DATA/'last_update.json'

CORE=['acoustic','sonar','ultrasound','photoacoustic','optoacoustic','acousto-optic','acousto optic']
IMAGING=['imaging','reconstruction','tomography','holography','nlos','non-line-of-sight','synthetic aperture','sensor fusion','neural rendering','volume rendering','differentiable rendering','3d','bathymetry','surface reconstruction']
PRIMARY=['imaging sonar','forward-looking sonar','synthetic aperture sonar','camera sonar','camera-sonar','acoustic-optical','acoustic optical','opti-acoustic','acoustic non-line-of-sight','acoustic nlos','ultrasound synthetic aperture','acoustic holography','coded acoustic','computational ultrasound']
NEG=['speech recognition','music','audio caption','radio galaxy','black hole','x-ray binary','tidal disruption','cell culture','ball games','raman data fusion','millimetre arrays','co2 leakage','injection wells','fuel']
TOPICS=[('camera-sonar fusion',['camera sonar','camera-sonar','vision sonar','acoustic-optical','acoustic optical','opti-acoustic']),('synthetic aperture sonar',['synthetic aperture sonar','coherent synthetic aperture']),('imaging sonar',['imaging sonar','forward-looking sonar']),('acoustic NLOS',['non-line-of-sight','non line of sight','nlos']),('acoustic holography',['acoustic holograph','phased array']),('acoustic coded imaging',['coded imaging','temporal encoding','complex field','coded acoustic']),('differentiable acoustic rendering',['differentiable rendering','neural volume rendering','neural implicit','sonar rendering']),('photoacoustic imaging',['photoacoustic','optoacoustic']),('acousto-optic imaging',['acousto-optic','acousto optic']),('computational ultrasound',['computational ultrasound','ultrasound reconstruction']),('3D reconstruction',['3d reconstruction','volumetric','tomography','bathymetry'])]
VENUE_PATTERNS=[('Nature Portfolio',[r'\bnature\b',r'nature communications',r'communications physics',r'scientific data',r'light: science']),('Science family',[r'\bscience\b',r'science advances',r'science robotics']),('ACM TOG / SIGGRAPH',[r'acm transactions on graphics',r'\btog\b',r'\bsiggraph\b',r'siggraph asia']),('IEEE TPAMI',[r'pattern analysis and machine intelligence',r'\btpami\b']),('IEEE TIP',[r'transactions on image processing',r'\btip\b']),('CVPR',[r'\bcvpr\b',r'computer vision and pattern recognition']),('ICCV',[r'\biccv\b']),('ECCV',[r'\beccv\b']),('ICLR',[r'\biclr\b']),('NeurIPS',[r'\bneurips\b',r'neural information processing systems'])]
SESSION=requests.Session(); SESSION.headers.update({'User-Agent':'acoustic-optics-imaging-agent-audit/1.2 (https://github.com/ruixv/acoustic-optics-imaging; mailto:%s)'%os.getenv('CROSSREF_MAILTO','example@example.com')})

def load(p:Path,d:Any): return json.loads(p.read_text(encoding='utf-8')) if p.exists() else d

def dump(p:Path,o:Any): p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def norm(s:str)->str: return re.sub(r'[^a-z0-9]+',' ',(s or '').lower()).strip()

def sim(a:str,b:str)->float: return SequenceMatcher(None,norm(a),norm(b)).ratio() if norm(a) and norm(b) else 0.0

def fp(x:Dict[str,Any])->str: return hashlib.sha1(((x.get('doi') or x.get('title') or x.get('primary_url') or '').lower()).encode()).hexdigest()[:12]

def title_key(x:Dict[str,Any])->str: return norm(x.get('title',''))

def group(venue:str,title:str='')->str:
    v=(venue or '').lower(); t=(title or '').lower()
    for g, pats in VENUE_PATTERNS:
        if any(re.search(p,v) for p in pats): return g
    if any(re.search(p,t) for p in [r'\bsiggraph\b',r'\bcvpr\b',r'\biccv\b',r'\beccv\b',r'\biclr\b',r'\bneurips\b']):
        for g,pats in VENUE_PATTERNS:
            if any(re.search(p,t) for p in pats): return g
    if v=='arxiv preprint': return 'arXiv'
    return 'Other'

def topics(item:Dict[str,Any])->List[str]:
    s=' '.join(str(item.get(k,'')) for k in ['title','abstract','matched_query']).lower(); out=[]
    for label,keys in TOPICS:
        if any(k in s for k in keys): out.append(label)
    return out[:6] or [w for w in re.split(r'\W+',item.get('matched_query','')) if len(w)>4][:4]

def clean_text(s:str)->str:
    s=str(s or ''); scope=chr(0x4E0E)+chr(0x4F60)+chr(0x7684); poss=chr(0x4F60)+chr(0x7684)
    s=re.sub(re.escape(scope)+r'[“\"][^。]*[”\"][^。]*。?','该论文与公开追踪主题直接相关，并提供可核验来源。',s)
    return s.replace(poss,'该')

def sanitize(papers:List[Dict[str,Any]]):
    changed=False
    for p in papers:
        for k,v in list(p.items()):
            if isinstance(v,str):
                nv=clean_text(v)
                if nv!=v: p[k]=nv; changed=True
    return changed

def date_from_crossref(item:Dict[str,Any]):
    for k in ['published-print','published-online','published','issued','created']:
        parts=(item.get(k) or {}).get('date-parts')
        if parts and parts[0]:
            arr=parts[0]; y=int(arr[0]) if arr and arr[0] else None; m=int(arr[1]) if len(arr)>1 else 1; d=int(arr[2]) if len(arr)>2 else 1
            if y: return y,f'{y:04d}-{m:02d}-{d:02d}'
    return None,''

def crossref_final_lookup(title:str)->Optional[Dict[str,Any]]:
    if not title: return None
    params={'query.title':title,'rows':5,'select':'DOI,title,author,container-title,published-print,published-online,published,issued,created,URL,type'}
    if os.getenv('CROSSREF_MAILTO'): params['mailto']=os.getenv('CROSSREF_MAILTO')
    try:
        r=SESSION.get('https://api.crossref.org/works?'+urllib.parse.urlencode(params),timeout=30); r.raise_for_status(); items=r.json().get('message',{}).get('items',[])
    except Exception: return None
    best=None; best_score=0.0
    for it in items:
        cr_title=' '.join(it.get('title') or []); venue=' '.join(it.get('container-title') or []); doi=it.get('DOI') or ''; score=sim(title,cr_title)
        if score>best_score and score>=0.92 and venue and doi:
            best=it; best_score=score
    if not best: return None
    y,pub=date_from_crossref(best); authors=[]
    for a in best.get('author') or []:
        nm=' '.join([a.get('given',''),a.get('family','')]).strip()
        if nm: authors.append(nm)
    venue=' '.join(best.get('container-title') or []); doi=best.get('DOI') or ''
    return {'title':' '.join(best.get('title') or []) or title,'authors':'; '.join(authors[:8])+('; et al.' if len(authors)>8 else ''),'year':y,'publication_date':pub,'venue':venue,'venue_group':group(venue,title),'doi':doi,'primary_url':best.get('URL') or (f'https://doi.org/{doi}' if doi else ''),'source':'Crossref-final-version','final_version_resolved':True,'final_version_similarity':round(best_score,3)}

def resolve_final_version(c:Dict[str,Any])->Dict[str,Any]:
    is_arxiv=(c.get('source')=='arXiv') or (str(c.get('venue','')).lower()=='arxiv preprint')
    if not is_arxiv: return c
    resolved=crossref_final_lookup(c.get('title',''))
    if not resolved:
        c['final_version_status']='arxiv-only-no-final-version-found'; return c
    arxiv_url=c.get('primary_url','') if 'arxiv.org' in c.get('primary_url','') else ''; arxiv_pdf=c.get('pdf_url','') if 'arxiv.org' in c.get('pdf_url','') else ''
    c.update({k:v for k,v in resolved.items() if v not in [None,'',[]]});
    if arxiv_pdf: c['pdf_url']=arxiv_pdf
    sources=c.get('sources') or []
    for u in [c.get('primary_url'),arxiv_url,arxiv_pdf]:
        if u and u not in sources: sources.append(u)
    c['sources']=sources; c['final_version_status']='resolved-from-arxiv-to-final-venue'; return c

def audit(c:Dict[str,Any])->Dict[str,Any]:
    c=resolve_final_version(c); text=' '.join(str(c.get(k,'')) for k in ['title','abstract','venue','matched_query']).lower()
    vg=group(c.get('venue',''),c.get('title','')); c['venue_group']=c.get('venue_group') if c.get('venue_group') not in ['',None,'Nature Portfolio'] or vg=='Other' else vg; c['topics']=c.get('topics') or topics(c)
    score=int(c.get('score') or 0); top=c.get('venue_group') not in ['Other','arXiv']; primary=any(x in text for x in PRIMARY); core=any(x in text for x in CORE); img=any(x in text for x in IMAGING); neg=any(x in text for x in NEG)
    preprint=(str(c.get('venue','')).lower()=='arxiv preprint') or (c.get('source')=='arXiv' and not c.get('doi'))
    source_ok=bool(c.get('doi')) or c.get('source') in ['Crossref','Crossref-final-version','CVF','OpenReview']
    decision='candidate'; conf=max(.1,min(.75,score/15))
    if score>=12 and primary and img and source_ok and not preprint and not neg:
        decision='promote'; conf=.88
    elif score>=9 and primary and img and not neg:
        decision='approved-candidate'; conf=.72
    elif neg or not (primary or (core and img)):
        decision='reject-like'; conf=.2
    c['status']='agent-promoted' if decision=='promote' else ('agent-approved-candidate' if decision=='approved-candidate' else 'agent-watchlist')
    c['agent_audit']={'decision':decision,'confidence':conf,'checks':{'top_venue':top,'primary_scope':primary,'core_term':core,'imaging_term':img,'source_ok':source_ok,'preprint_only':preprint,'negative_filter':neg,'final_version_status':c.get('final_version_status','not-needed')}}
    return c

def to_paper(c:Dict[str,Any])->Dict[str,Any]:
    today=dt.date.today().isoformat(); ts=c.get('topics') or topics(c); doi=c.get('doi',''); venue=c.get('venue','')
    rel='core' if any(x in ts for x in ['camera-sonar fusion','synthetic aperture sonar','imaging sonar','acoustic NLOS','differentiable acoustic rendering','photoacoustic imaging','acousto-optic imaging','acoustic holography']) else 'related'
    venue_type='preprint' if venue.lower()=='arxiv preprint' else ('journal' if any(x in venue.lower() for x in ['nature','science','communications','journal','transactions']) else 'conference')
    sources=[]
    for u in [c.get('primary_url'),('https://doi.org/'+doi if doi else ''),*(c.get('sources') or [])]:
        if u and u not in sources: sources.append(u)
    return {'id':c.get('id') or ('auto-'+fp(c)),'title':c.get('title',''),'authors':c.get('authors',''),'year':c.get('year'),'publication_date':c.get('publication_date',''),'venue':venue,'venue_group':c.get('venue_group') or group(venue,c.get('title','')),'venue_type':venue_type,'doi':doi,'primary_url':c.get('primary_url',''),'pdf_url':c.get('pdf_url',''),'project_url':'','code_url':'','topics':ts,'relevance':rel,'summary_en':'Automatically audited paper on '+(', '.join(ts) or 'acoustic imaging')+'.','summary_cn':'自动审核收录的论文，主题包括 '+('、'.join(ts) or '声学成像')+'。','why_include_en':'Promoted by the automatic curation agent based on public source quality, topical relevance, final-version resolution, and duplicate checks.','why_include_cn':'由自动文献审核 Agent 根据公开来源质量、主题相关性、最终发表版本解析和重复检查自动收录。','download_note':'The venue records the final accepted/published version when available; arXiv is used only for preprints or as an open PDF source.','sources':sources,'last_verified':today,'verification':{'mode':'automatic-curation-agent','confidence':c.get('agent_audit',{}).get('confidence'),'source':c.get('source',''),'final_version_status':c.get('final_version_status','not-needed')}}

def main():
    papers=load(PAPERS,[]); focus=load(FOCUS,[]); cands=load(CANDS,[]); sanitize(papers); sanitize(focus)
    keys={fp(p) for p in papers+focus}; title_keys={title_key(p) for p in papers+focus}; promoted=[]; kept=[]; resolved=0
    for c in cands:
        c=audit(c)
        if c.get('final_version_status')=='resolved-from-arxiv-to-final-venue': resolved+=1
        k,tk=fp(c),title_key(c)
        if c.get('agent_audit',{}).get('decision')=='promote' and k not in keys and tk not in title_keys:
            p=to_paper(c); papers.append(p); keys.add(k); title_keys.add(tk); promoted.append(p); c['promoted_on']=dt.date.today().isoformat()
        else: kept.append(c)
    papers.sort(key=lambda p:(str(p.get('publication_date') or p.get('year') or ''),p.get('title','')),reverse=True)
    kept.sort(key=lambda c:(c.get('agent_audit',{}).get('confidence',0),c.get('score',0),str(c.get('publication_date',''))),reverse=True)
    dump(PAPERS,papers); dump(FOCUS,focus); dump(CANDS,kept)
    log=load(LOG,{})
    log.update({'agent_audit_last_run':dt.datetime.now(dt.timezone.utc).isoformat(),'promoted_count':len(promoted),'resolved_final_versions':resolved,'audit_note':'High-confidence records are promoted automatically. Scope is narrowed to acoustic imaging, imaging sonar, acoustic rendering/reconstruction, and acoustic-optical fusion.'})
    dump(LOG,log); print(f'agent audit promoted {len(promoted)} papers; resolved {resolved} arXiv final versions; kept {len(kept)} candidates')
if __name__=='__main__': main()
