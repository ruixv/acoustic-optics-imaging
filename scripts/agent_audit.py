#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import json, re, datetime as dt, hashlib

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
PAPERS=DATA/'papers.json'
CANDS=DATA/'candidates.json'
LOG=DATA/'last_update.json'

TOP_GROUPS=['Nature','Nature Portfolio','Science family','ACM SIGGRAPH','ACM TOG / SIGGRAPH','ACM TOG / SIGGRAPH Asia','IEEE TPAMI','IEEE TIP','CVPR','ICCV','ECCV','ICLR','NeurIPS']
CORE=['acoustic','sonar','ultrasound','photoacoustic','optoacoustic','acousto-optic','acousto optic']
IMAGING=['imaging','reconstruction','tomography','holography','nlos','non-line-of-sight','synthetic aperture','sensor fusion','gaussian splatting','neural rendering','3d']
NEG=['speech recognition','music','audio caption','radio galaxy','black hole','x-ray binary','tidal disruption','cell culture','ball games','raman data fusion','millimetre arrays']
TOPICS=[('camera-sonar fusion',['camera sonar','camera-sonar','vision sonar','acoustic-optical','acoustic optical']),('synthetic aperture sonar',['synthetic aperture sonar','coherent synthetic aperture']),('acoustic NLOS',['non-line-of-sight','non line of sight','nlos']),('acoustic holography',['acoustic holograph','phased array']),('acoustic coded imaging',['coded imaging','temporal encoding','complex field','coded']),('photoacoustic imaging',['photoacoustic','optoacoustic']),('acousto-optic imaging',['acousto-optic','acousto optic']),('computational ultrasound',['computational ultrasound','ultrasound reconstruction']),('neural rendering',['neural rendering','gaussian splatting']),('3D reconstruction',['3d reconstruction','volumetric','tomography'])]

def load(p,d): return json.loads(p.read_text(encoding='utf-8')) if p.exists() else d

def dump(p,o): p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def fp(x): return hashlib.sha1(((x.get('doi') or x.get('title') or x.get('primary_url') or '').lower()).encode()).hexdigest()[:12]

def group(venue,title=''):
    s=(venue+' '+title).lower()
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

def topics(item):
    s=' '.join(str(item.get(k,'')) for k in ['title','abstract','matched_query']).lower(); out=[]
    for label,keys in TOPICS:
        if any(k in s for k in keys): out.append(label)
    return out[:6] or [w for w in re.split(r'\W+',item.get('matched_query','')) if len(w)>4][:4]

def clean_text(s):
    s=str(s or ''); scope=chr(0x4E0E)+chr(0x4F60)+chr(0x7684); poss=chr(0x4F60)+chr(0x7684)
    s=re.sub(re.escape(scope)+r'[“\"][^。]*[”\"][^。]*。?','该论文与公开追踪主题直接相关，并提供可核验来源。',s)
    return s.replace(poss,'该')

def sanitize_papers(papers):
    changed=False
    for p in papers:
        for k,v in list(p.items()):
            if isinstance(v,str):
                nv=clean_text(v)
                if nv!=v: p[k]=nv; changed=True
    return changed

def audit(c):
    text=' '.join(str(c.get(k,'')) for k in ['title','abstract','venue','matched_query']).lower()
    vg=group(c.get('venue',''),c.get('title','')); c['venue_group']=vg; c['topics']=topics(c)
    score=int(c.get('score') or 0); top=vg!='Other' or 'top-venue-hint' in c.get('reasons',[])
    core=any(x in text for x in CORE); img=any(x in text for x in IMAGING); neg=any(x in text for x in NEG)
    source_ok=bool(c.get('doi')) or c.get('source') in ['Crossref','CVF','OpenReview']; preprint=c.get('source')=='arXiv' and not c.get('doi')
    decision='candidate'; conf=max(.1,min(.75,score/15))
    if score>=12 and top and core and img and source_ok and not preprint and not neg:
        decision='promote'; conf=.88
    elif score>=9 and top and core and img and not neg:
        decision='approved-candidate'; conf=.72
    elif neg:
        decision='reject-like'; conf=.25
    c['status']='agent-promoted' if decision=='promote' else ('agent-approved-candidate' if decision=='approved-candidate' else 'agent-watchlist')
    c['agent_audit']={'decision':decision,'confidence':conf,'checks':{'top_venue':top,'core_term':core,'imaging_term':img,'source_ok':source_ok,'preprint_only':preprint,'negative_filter':neg}}
    return c

def to_paper(c):
    today=dt.date.today().isoformat(); ts=c.get('topics') or topics(c)
    rel='core' if any(x in ts for x in ['camera-sonar fusion','synthetic aperture sonar','acoustic NLOS','photoacoustic imaging','acousto-optic imaging','acoustic holography']) else 'related'
    doi=c.get('doi','')
    return {'id':c.get('id') or ('auto-'+fp(c)),'title':c.get('title',''),'authors':c.get('authors',''),'year':c.get('year'),'publication_date':c.get('publication_date',''),'venue':c.get('venue',''),'venue_group':c.get('venue_group') or group(c.get('venue',''),c.get('title','')),'venue_type':'journal' if any(x in (c.get('venue','').lower()) for x in ['nature','science','communications','journal','transactions']) else 'conference','doi':doi,'primary_url':c.get('primary_url',''),'pdf_url':c.get('pdf_url',''),'project_url':'','code_url':'','topics':ts,'relevance':rel,'summary_en':'Automatically audited paper on '+(', '.join(ts) or 'acoustic–optical imaging')+'.','summary_cn':'自动审核收录的论文，主题包括 '+('、'.join(ts) or '声光/声学成像')+'。','why_include_en':'Promoted by the automatic curation agent based on source quality, venue priority, topical relevance, recency, and duplicate checks.','why_include_cn':'由自动文献审核 Agent 根据来源质量、venue 优先级、主题相关性、时效性和重复检查自动收录。','download_note':'PDF URL is recorded only when an open or publisher/author source is available.','sources':[u for u in [c.get('primary_url'),('https://doi.org/'+doi if doi else '')] if u],'last_verified':today,'verification':{'mode':'automatic-curation-agent','confidence':c.get('agent_audit',{}).get('confidence'),'source':c.get('source','')}}

def main():
    papers=load(PAPERS,[]); cands=load(CANDS,[]); sanitize_papers(papers)
    keys={fp(p) for p in papers}; promoted=[]; kept=[]
    for c in cands:
        c=audit(c); k=fp(c)
        if c.get('agent_audit',{}).get('decision')=='promote' and k not in keys:
            p=to_paper(c); papers.append(p); keys.add(k); promoted.append(p); c['promoted_on']=dt.date.today().isoformat()
        else:
            kept.append(c)
    papers.sort(key=lambda p:(str(p.get('publication_date') or p.get('year') or ''),p.get('title','')),reverse=True)
    kept.sort(key=lambda c:(c.get('agent_audit',{}).get('confidence',0),c.get('score',0),str(c.get('publication_date',''))),reverse=True)
    dump(PAPERS,papers); dump(CANDS,kept)
    log=load(LOG,{})
    log.update({'agent_audit_last_run':dt.datetime.now(dt.timezone.utc).isoformat(),'promoted_count':len(promoted),'audit_note':'High-confidence records are promoted automatically; borderline records remain in data/candidates.json.'})
    dump(LOG,log)
    print(f'agent audit promoted {len(promoted)} papers; kept {len(kept)} candidates')
if __name__=='__main__': main()
