#!/usr/bin/env python3
"""Scheduled discovery step for the acoustic-optics imaging tracker.

Scope: acoustic imaging, imaging sonar, acoustic-optical fusion, acoustic NLOS,
acoustic holography/coded acoustics, differentiable acoustic reconstruction,
and the optional hidden mmWave radar imaging side-track.

Discovery combines keyword search with citation-graph expansion from records
already labeled as Core. Citation-of-Core is a strong candidate signal, not an
automatic promotion rule.
"""
from __future__ import annotations
import argparse, datetime as dt, hashlib, html, json, os, re, time, urllib.parse, xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
import requests

ROOT=Path(__file__).resolve().parents[1]
DATA_DIR=ROOT/'data'; DATA_DIR.mkdir(exist_ok=True)
PAPERS_PATH=DATA_DIR/'papers.json'; FOCUS_PATH=DATA_DIR/'focus_papers.json'; MMWAVE_PATH=DATA_DIR/'mmwave_papers.json'; CANDIDATES_PATH=DATA_DIR/'candidates.json'; RUN_LOG_PATH=DATA_DIR/'last_update.json'

TOP_VENUE_PATTERNS=[
    r'\bnature\b',r'nature communications',r'nature biomedical engineering',r'nature electronics',r'nature photonics',
    r'nature machine intelligence',r'nature computational science',r'communications engineering',r'communications physics',
    r'communications materials',r'communications medicine',r'scientific data',r'light: science',
    r'\bscience\b',r'science advances',r'science robotics',
    r'acm transactions on graphics',r'\bsiggraph\b',r'\bcvpr\b',r'\biccv\b',r'\beccv\b',r'\biclr\b',r'\bicml\b',r'\biccp\b',
    r'international conference on machine learning',r'international conference on computational photography',r'\bneurips\b',
    r'pattern analysis and machine intelligence',r'\btpami\b',r'transactions on image processing',r'\btip\b',
    r'\bmobisys\b',r'\bmobicom\b',r'\bsensys\b',r'transactions on mobile computing',r'\btmc\b'
]
QUERIES=[
'imaging sonar differentiable rendering','neural implicit surface reconstruction imaging sonar','neural volume rendering imaging sonar','forward-looking sonar 3D reconstruction differentiable','synthetic aperture sonar neural reconstruction','coherent synthetic aperture sonar reconstruction','camera sonar fusion 3D reconstruction','acoustic optical sensor fusion sonar','opti acoustic sensor fusion volumetric mapping','sonar visual dataset cross modal underwater perception','visual inertial sonar SLAM photometric rendering','VISO Robust Underwater Visual-Inertial-Sonar SLAM','SonarSweep Fusing Sonar Vision Robust 3D Reconstruction','Towards Realistic 3D Sonar Simulation','volumetric 3D sonar simulation acoustic propagation','acoustic non-line-of-sight imaging','ultrasound synthetic aperture non-line-of-sight imaging','acoustic holography phased array computation','acoustic disguising cloaking holography','acoustic cloning holographic scattering object','coded acoustic imaging computational acoustics','computational ultrasound complex fields imaging','acousto-optic imaging speckle decorrelation','photoacoustic imaging acoustic hologram',
'NAS-GS noise-aware sonar Gaussian splatting','circular synthetic aperture sonar shadows 3D reconstruction','differentiable structural optimization acoustic holography','skull-conforming acoustic holographic lenses','vectorial acoustic multiplexed holography','compact optical-resolution photoacoustic microscopy reflective objective transducer',
'mmWave radar imaging CVPR','mmWave radar imaging ICCV','mmWave radar imaging NeurIPS','mmWave radar imaging ECCV','mmWave radar imaging ICLR','mmWave radar imaging ICML','mmWave radar imaging ICCP','mmWave radar imaging MobiSys','mmWave radar imaging MobiCom','mmWave radar imaging SenSys','mmWave radar imaging TPAMI','mmWave radar imaging TOG','mmWave radar imaging TIP','mmWave radar imaging TMC','millimeter wave radar imaging SIGGRAPH','4D radar point cloud CVPR','FMCW MIMO-SAR radar imaging MobiSys','millimeter wave radar indoor mapping MobiSys',
'handheld mmWave SAR autofocus phase error compensation','handheld millimeter-wave imaging phase error estimation compensation','IFNet deep imaging focusing handheld SAR millimeter-wave','TwinFocus autofocus handheld mmWave SAR physical digital twin references','mmWave surface normal estimation through-occlusion 3D reconstruction','mmNorm millimeter-wave surface normal hidden object reconstruction','Wave-Former through-occlusion 3D reconstruction wireless shape completion','single static radar indoor scene understanding RISE','mmWave multipath indoor layout reconstruction object detection','Nature Portfolio Communications Engineering millimeter-wave imaging'
]
CORE_TERMS=['acoustic','sonar','ultrasound','photoacoustic','optoacoustic','acousto-optic','acousto optic','radar','mmwave','millimeter-wave','millimeter wave','millimetre wave','fmcw','wireless']
IMAGING_TERMS=['imaging','reconstruction','tomography','holography','nlos','non-line-of-sight','synthetic aperture','sensor fusion','neural rendering','volume rendering','differentiable rendering','3d','bathymetry','surface reconstruction','point cloud','super resolution','mapping','surface normal','through-occlusion','shape completion','scene understanding','autofocus','phase error','phase compensation','phase calibration','gaussian splatting','novel view synthesis','multiplexed holography','wavefront shaping','lens optimization','cloaking','disguising','scattering signature','wave cloning','plane sweeping','photometric rendering','volumetric sensing','sim-to-real']
PRIMARY_TERMS=['imaging sonar','forward-looking sonar','synthetic aperture sonar','camera sonar','camera-sonar','sonar vision','vision sonar','visual-inertial-sonar','visual inertial sonar','sonarsweep','3d sonar','volumetric 3d sonar','sonar simulation','photometric sonar rendering','sonar gaussian splatting','noise-aware sonar','circular synthetic aperture sonar','acoustic-optical','acoustic optical','opti-acoustic','acoustic non-line-of-sight','acoustic nlos','ultrasound synthetic aperture','acoustic holography','acoustic holographic','acoustic holographic lens','acoustic disguising','acoustic cloaking','acoustic cloning','skull-conforming acoustic','vectorial acoustic multiplexed holography','coded acoustic','computational ultrasound','photoacoustic microscopy','optical-resolution photoacoustic microscopy','or-pam','reflective objective','mmwave radar','millimeter-wave radar','millimeter wave radar','millimetre wave radar','4d radar','radar point cloud','mimo-sar','fmcw radar','radar imaging','mmwave imaging','millimeter wave imaging','millimetre wave mapping','handheld sar','handheld mmwave','mmwave sar','single static radar','radar indoor scene understanding','through-occlusion','surface normal estimation','wireless shape completion','mmnorm','twinfocus','ifnet','phase error estimation']
NEGATIVE_TERMS=['speech recognition','music','audio caption','radio galaxy','black hole','x-ray binary','tidal disruption','cell culture','raman data fusion','football','ball games','co2 leakage','injection wells','fuel','cosmology','dark matter','dark energy','epidemiological','telescope','telescopy']
SESSION=requests.Session(); SESSION.headers.update({'User-Agent':'acoustic-optics-imaging-updater/2.8 (https://github.com/ruixv/acoustic-optics-imaging; mailto:%s)'%os.getenv('CROSSREF_MAILTO','example@example.com')})

def norm_text(x:str)->str: return re.sub(r'\s+',' ',(x or '').strip())
def slugify(s:str,max_len:int=80)->str: return re.sub(r'[^a-zA-Z0-9]+','-',s.lower()).strip('-')[:max_len].strip('-') or 'candidate'
def fingerprint(title:str,doi:str='',url:str='')->str: return hashlib.sha1((doi or title or url).lower().strip().encode('utf-8')).hexdigest()[:12]
def load_json(path:Path,default:Any)->Any: return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default
def write_json(path:Path,obj:Any)->None: path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def is_top_venue(venue:str)->bool: return any(re.search(p,(venue or '').lower()) for p in TOP_VENUE_PATTERNS)
def get_year_date_crossref(item:Dict[str,Any])->Tuple[Optional[int],str]:
    for k in ['published-print','published-online','published','created','issued']:
        parts=(item.get(k) or {}).get('date-parts')
        if parts and parts[0]:
            arr=parts[0]; y=int(arr[0]) if arr and arr[0] else None; m=int(arr[1]) if len(arr)>1 else 1; d=int(arr[2]) if len(arr)>2 else 1
            if y: return y,f'{y:04d}-{m:02d}-{d:02d}'
    return None,''
def relevant_enough(title:str,abstract:str,venue:str,query:str)->bool:
    text=f'{title} {abstract} {venue} {query}'.lower()
    if any(t in text for t in NEGATIVE_TERMS): return False
    primary=any(t in text for t in PRIMARY_TERMS); core=any(t in text for t in CORE_TERMS); imaging=any(t in text for t in IMAGING_TERMS)
    return primary or (core and imaging)
def citation_relevant_enough(title:str,abstract:str,venue:str,core_paper:Dict[str,Any])->bool:
    core_title=core_paper.get('title',''); core_topics=' '.join(core_paper.get('topics') or [])
    if relevant_enough(title,abstract,venue,f'{core_title} {core_topics}'): return True
    text=f'{title} {abstract} {venue}'.lower()
    if any(t in text for t in NEGATIVE_TERMS): return False
    core_context=f'{core_title} {core_topics}'.lower(); seed_terms=[t for t in PRIMARY_TERMS+CORE_TERMS+IMAGING_TERMS if t in core_context]
    return any(t in text for t in seed_terms)
def score_candidate(title:str,abstract:str,venue:str,query:str,year:Optional[int])->Tuple[int,List[str]]:
    text=f'{title} {abstract} {venue}'.lower(); reasons=[]; score=0
    if is_top_venue(venue): score+=4; reasons.append('top-venue')
    if any(t in text for t in PRIMARY_TERMS): score+=5; reasons.append('primary imaging/radar term')
    elif any(t in text for t in CORE_TERMS): score+=2; reasons.append('core wave-sensing term')
    if any(t in text for t in IMAGING_TERMS): score+=3; reasons.append('imaging/reconstruction term')
    if any(t in text for t in NEGATIVE_TERMS): score-=8; reasons.append('negative-topic-filter')
    q_terms=[w for w in re.split(r'\W+',query.lower()) if len(w)>3]; hits=sum(1 for w in q_terms if w in text)
    if q_terms and hits>=max(2,len(q_terms)//2): score+=2; reasons.append('query-title/abstract match')
    if year and year>=dt.date.today().year-2: score+=1; reasons.append('recent')
    return score,reasons
def record_base(title,authors,year,pub_date,venue,doi,url,pdf,source,query,score,reasons):
    return {'id':slugify(f"{year or 'yyyy'}-{title}")+'-'+fingerprint(title,doi,url),'title':title,'authors':authors,'year':year,'publication_date':pub_date,'venue':venue,'doi':doi,'primary_url':url,'pdf_url':pdf,'source':source,'matched_query':query,'score':score,'reasons':reasons,'status':'candidate-pending-agent-audit'}

def crossref_search(query:str,rows:int,from_date:str)->List[Dict[str,Any]]:
    params={'query.bibliographic':query,'rows':rows,'sort':'published','order':'desc','filter':f'from-pub-date:{from_date}','select':'DOI,title,author,container-title,published-print,published-online,published,issued,created,URL,type,abstract'}
    if os.getenv('CROSSREF_MAILTO'): params['mailto']=os.getenv('CROSSREF_MAILTO')
    r=SESSION.get('https://api.crossref.org/works?'+urllib.parse.urlencode(params),timeout=45); r.raise_for_status(); out=[]
    for it in r.json().get('message',{}).get('items',[]):
        title=norm_text(' '.join(it.get('title') or []))
        if not title: continue
        venue=norm_text(' '.join(it.get('container-title') or [])); abstract=re.sub(r'<[^>]+>',' ',html.unescape(it.get('abstract') or '')); year,pub=get_year_date_crossref(it)
        if not relevant_enough(title,abstract,venue,query): continue
        authors=[]
        for a in it.get('author') or []:
            name=norm_text(' '.join([a.get('given',''),a.get('family','')]))
            if name: authors.append(name)
        doi=it.get('DOI') or ''; url=it.get('URL') or (f'https://doi.org/{doi}' if doi else ''); score,reasons=score_candidate(title,abstract,venue,query,year)
        out.append(record_base(title,'; '.join(authors),year,pub,venue,doi,url,'','Crossref',query,score,reasons))
    return out
def arxiv_search(query:str,rows:int,from_date:str)->List[Dict[str,Any]]:
    terms=[t for t in re.split(r'\s+',query.strip()) if len(t)>3]; search_query=' AND '.join([f'all:"{term}"' for term in terms]) or f'all:"{query}"'
    params={'search_query':search_query,'start':0,'max_results':rows,'sortBy':'submittedDate','sortOrder':'descending'}
    r=SESSION.get('http://export.arxiv.org/api/query?'+urllib.parse.urlencode(params),timeout=45); r.raise_for_status(); root=ET.fromstring(r.text); ns={'a':'http://www.w3.org/2005/Atom'}; cutoff=dt.date.fromisoformat(from_date); out=[]
    for e in root.findall('a:entry',ns):
        title=norm_text(e.findtext('a:title',default='',namespaces=ns)); summary=norm_text(e.findtext('a:summary',default='',namespaces=ns)); published=e.findtext('a:published',default='',namespaces=ns); pub=published[:10] if published else ''
        if pub:
            try:
                if dt.date.fromisoformat(pub)<cutoff: continue
            except ValueError: pass
        if not relevant_enough(title,summary,'arXiv preprint',query): continue
        year=int(pub[:4]) if pub[:4].isdigit() else None; authors='; '.join(norm_text(a.findtext('a:name',default='',namespaces=ns)) for a in e.findall('a:author',ns)); entry_id=e.findtext('a:id',default='',namespaces=ns); pdf=''
        for link in e.findall('a:link',ns):
            if link.attrib.get('title')=='pdf' or link.attrib.get('type')=='application/pdf': pdf=link.attrib.get('href','')
        score,reasons=score_candidate(title,summary,'arXiv preprint',query,year); out.append(record_base(title,authors,year,pub,'arXiv preprint','',entry_id,pdf,'arXiv',query,score,reasons))
    return out

def abstract_from_openalex(inv:Any)->str:
    if not isinstance(inv,dict): return ''
    pairs=[]
    for word,positions in inv.items():
        for pos in positions or []:
            if isinstance(pos,int): pairs.append((pos,word))
    return norm_text(' '.join(word for _,word in sorted(pairs)))
def normalize_openalex_doi(doi_url:str)->str: return re.sub(r'^https?://(dx\.)?doi\.org/','',(doi_url or '').strip(),flags=re.I)
def openalex_short_id(work_id:str)->str:
    m=re.search(r'(W\d+)$',work_id or ''); return m.group(1) if m else work_id
def openalex_params(**kwargs:Any)->Dict[str,Any]:
    params={k:v for k,v in kwargs.items() if v not in [None,'',[]]}
    if os.getenv('CROSSREF_MAILTO'): params['mailto']=os.getenv('CROSSREF_MAILTO')
    return params
def resolve_openalex_work(core_paper:Dict[str,Any])->Optional[Dict[str,Any]]:
    doi=normalize_openalex_doi(core_paper.get('doi','')); title=core_paper.get('title','')
    if doi:
        url='https://api.openalex.org/works/'+urllib.parse.quote(f'doi:{doi}',safe=':')
        r=SESSION.get(url,params=openalex_params(),timeout=45)
        if r.status_code==200: return r.json()
        if r.status_code not in (400,404): r.raise_for_status()
    if title:
        r=SESSION.get('https://api.openalex.org/works',params=openalex_params(search=title,**{'per-page':1,'select':'id,display_name,doi,publication_year,publication_date'}),timeout=45); r.raise_for_status()
        results=r.json().get('results') or []
        if results: return results[0]
    return None
def openalex_work_to_candidate(work:Dict[str,Any],core_paper:Dict[str,Any])->Optional[Dict[str,Any]]:
    title=norm_text(work.get('display_name') or work.get('title') or '')
    if not title: return None
    loc=work.get('primary_location') or {}; source_obj=loc.get('source') or {}; venue=norm_text(source_obj.get('display_name') or ((work.get('host_venue') or {}).get('display_name')) or 'OpenAlex indexed work')
    abstract=abstract_from_openalex(work.get('abstract_inverted_index'))
    if not citation_relevant_enough(title,abstract,venue,core_paper): return None
    year=work.get('publication_year'); pub=work.get('publication_date') or (f'{int(year):04d}-01-01' if isinstance(year,int) else '')
    doi_url=work.get('doi') or ''; doi=normalize_openalex_doi(doi_url); primary_url=doi_url or loc.get('landing_page_url') or work.get('id') or ''; pdf_url=loc.get('pdf_url') or ((work.get('open_access') or {}).get('oa_url') or '')
    names=[((a.get('author') or {}).get('display_name') or '').strip() for a in work.get('authorships') or []]; names=[n for n in names if n]; authors='; '.join(names[:12])+('; et al.' if len(names)>12 else '')
    core_title=core_paper.get('title',''); query=f'cites core: {core_title}'; score,reasons=score_candidate(title,abstract,venue,query,year if isinstance(year,int) else None); score+=5; reasons.append('cites-core-paper')
    item=record_base(title,authors,year if isinstance(year,int) else None,pub,venue,doi,primary_url,pdf_url,'OpenAlex cited-by',query,score,reasons)
    item.update({'cites_core':True,'cited_core_paper':core_paper.get('id') or core_title,'cited_core_title':core_title,'cited_core_doi':core_paper.get('doi',''),'citation_source':'OpenAlex cited-by graph','metadata_verified_from':'OpenAlex'})
    return item
def core_papers_for_citation_expansion(verified:List[Dict[str,Any]],max_seeds:int)->List[Dict[str,Any]]:
    cores=[]; seen=set()
    for p in verified:
        if (p.get('relevance') or '').lower()!='core': continue
        key=fingerprint(p.get('title',''),p.get('doi',''),p.get('primary_url',''))
        if p.get('title') and key not in seen: seen.add(key); cores.append(p)
    cores.sort(key=lambda p:(p.get('year') or 0,p.get('publication_date') or ''),reverse=True); return cores[:max_seeds]
def openalex_citation_search(core_paper:Dict[str,Any],rows:int,from_date:str)->List[Dict[str,Any]]:
    seed=resolve_openalex_work(core_paper)
    if not seed or not seed.get('id'): return []
    seed_id=openalex_short_id(seed.get('id','')); fields='id,display_name,doi,publication_year,publication_date,primary_location,authorships,abstract_inverted_index,open_access'
    params=openalex_params(filter=f'cites:{seed_id},from_publication_date:{from_date}',sort='publication_date:desc',**{'per-page':rows,'select':fields})
    r=SESSION.get('https://api.openalex.org/works',params=params,timeout=45); r.raise_for_status(); out=[]
    for work in r.json().get('results') or []:
        item=openalex_work_to_candidate(work,core_paper)
        if item: out.append(item)
    return out

def merge_candidates(new_items:Iterable[Dict[str,Any]],existing:List[Dict[str,Any]],verified:List[Dict[str,Any]],min_score:int)->List[Dict[str,Any]]:
    verified_keys={fingerprint(p.get('title',''),p.get('doi',''),p.get('primary_url','')) for p in verified}; by_key={}; today=dt.date.today().isoformat()
    for item in existing: by_key[fingerprint(item.get('title',''),item.get('doi',''),item.get('primary_url',''))]=item
    for item in new_items:
        if item.get('score',0)<min_score: continue
        k=fingerprint(item.get('title',''),item.get('doi',''),item.get('primary_url',''))
        if k in verified_keys: continue
        if k in by_key:
            prev=by_key[k]; prev.update({kk:vv for kk,vv in item.items() if vv not in [None,'',[]]}); prev['last_seen']=today; prev['times_seen']=int(prev.get('times_seen',1))+1
        else: item['first_seen']=today; item['last_seen']=today; item['times_seen']=1; by_key[k]=item
    merged=list(by_key.values()); merged.sort(key=lambda x:(x.get('score',0),x.get('publication_date','')),reverse=True); return merged
def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--since-days',type=int,default=730); ap.add_argument('--rows',type=int,default=30); ap.add_argument('--min-score',type=int,default=7); ap.add_argument('--sleep',type=float,default=1.0); ap.add_argument('--citation-rows',type=int,default=80); ap.add_argument('--max-core-citation-seeds',type=int,default=50); ap.add_argument('--skip-citation-graph',action='store_true')
    args=ap.parse_args(); from_date=(dt.date.today()-dt.timedelta(days=args.since_days)).isoformat()
    verified=load_json(PAPERS_PATH,[])+load_json(FOCUS_PATH,[])+load_json(MMWAVE_PATH,[]); existing=load_json(CANDIDATES_PATH,[]); all_new=[]; errors=[]
    for q in QUERIES:
        for source_name,func in [('Crossref',crossref_search),('arXiv',arxiv_search)]:
            try: items=func(q,args.rows,from_date); all_new.extend(items); print(f'{source_name}: {q!r}: {len(items)} raw candidates')
            except Exception as e: print(f'ERROR {source_name} {q!r}: {e}'); errors.append({'source':source_name,'query':q,'error':str(e)})
            time.sleep(args.sleep)
    citation_seed_count=0
    if not args.skip_citation_graph:
        core_seeds=core_papers_for_citation_expansion(verified,args.max_core_citation_seeds); citation_seed_count=len(core_seeds)
        for core in core_seeds:
            query=f"cites core: {core.get('title','')}"
            try: items=openalex_citation_search(core,args.citation_rows,from_date); all_new.extend(items); print(f"OpenAlex cited-by: {core.get('id') or core.get('title')!r}: {len(items)} raw candidates")
            except Exception as e: print(f'ERROR OpenAlex cited-by {query!r}: {e}'); errors.append({'source':'OpenAlex cited-by','query':query,'error':str(e)})
            time.sleep(args.sleep)
    merged=merge_candidates(all_new,existing,verified,args.min_score); write_json(CANDIDATES_PATH,merged); write_json(RUN_LOG_PATH,{'last_run':dt.datetime.now(dt.timezone.utc).isoformat(),'since_date':from_date,'raw_candidates_seen':len(all_new),'saved_candidates_total':len(merged),'citation_graph_seed_count':citation_seed_count,'errors':errors,'note':'Candidates are ready for automatic curation-agent audit. arXiv search uses AND-style term matching plus a topical relevance gate to avoid broad OR false positives; author strings are preserved in full when available; the query set tracks recent 3D sonar simulation and vision-sonar fusion preprints; the updater also expands through OpenAlex cited-by links from Core papers.'}); print(f'saved {len(merged)} candidates to {CANDIDATES_PATH.relative_to(ROOT)}'); return 0
if __name__=='__main__': raise SystemExit(main())
