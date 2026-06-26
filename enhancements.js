(()=>{
  if(!document.body||document.body.dataset.page!=='index')return;

  const COPY={
    en:{
      navLatest:'Latest',navGraph:'Graph',
      latestEyebrow:'Latest Additions',latestTitle:'Latest Additions',
      latestSubtitle:'Recently added or re-verified papers, sorted by curation date first and publication date second.',
      latestStamp:'Added / checked',published:'Published',details:'Details',
      graphEyebrow:'Interactive graph',graphTitle:'Paper co-author graph',
      graphSubtitle:'Each node is one paper. Color encodes year. Two nodes are connected only when the currently recorded author metadata contains at least one shared author.',
      graphHint:'Click a node to inspect title, authors, venue, year, and co-author links.',
      graphIdle:'Select a node to inspect a paper and its co-author connections.',
      graphStats:'Graph summary',papers:'papers',edges:'co-author links',years:'years',
      selectedPaper:'Selected paper',sharedWith:'Co-author links',sharedAuthors:'Shared authors',noShared:'No co-author link is selected yet.',
      openDetails:'Open details',legend:'Year legend'
    },
    zh:{
      navLatest:'最新',navGraph:'关系图',
      latestEyebrow:'Latest Additions',latestTitle:'Latest Additions',
      latestSubtitle:'这里优先展示最近加入或重新核验的论文；排序先看收录/核验日期，再看论文发表日期。',
      latestStamp:'加入 / 核验',published:'发表',details:'详情',
      graphEyebrow:'交互式关系图',graphTitle:'论文共同作者关系图',
      graphSubtitle:'每个节点代表一篇论文；颜色代表年份；两篇论文只有在当前元数据中存在至少一位共同作者时才连边。',
      graphHint:'点击节点即可查看论文题目、作者、期刊/会议、年份以及共同作者连接。',
      graphIdle:'点击一个节点，查看该论文及其共同作者连接。',
      graphStats:'图谱概览',papers:'篇论文',edges:'条共同作者连边',years:'个年份',
      selectedPaper:'选中论文',sharedWith:'共同作者连接',sharedAuthors:'共同作者',noShared:'尚未选中共同作者连接。',
      openDetails:'打开详情',legend:'年份图例'
    }
  };

  let papers=[];
  let graph=null;
  let activeNode=-1;
  let resizeTimer=null;

  const $=s=>document.querySelector(s);
  const $$=s=>Array.from(document.querySelectorAll(s));
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const lang=()=>String(localStorage.getItem('aoi-lang')||document.documentElement.lang||'en').toLowerCase().startsWith('zh')?'zh':'en';
  const t=k=>(COPY[lang()]&&COPY[lang()][k])||COPY.en[k]||k;
  const yearOf=p=>String(p.year||String(p.publication_date||'').slice(0,4)||'Unknown');
  const dateKey=p=>String(p.added_at||p.curation_date||p.last_verified||p.first_seen||p.publication_date||p.year||'');
  const publicationKey=p=>String(p.publication_date||p.year||'');
  const topics=p=>(p.topics||[]).slice(0,4);
  const uniq=items=>{
    const m=new Map();
    items.forEach(p=>{if(p&&p.id&&!m.has(p.id))m.set(p.id,p)});
    return Array.from(m.values());
  };
  async function load(path){
    try{const r=await fetch(path,{cache:'no-store'});return r.ok?await r.json():[]}
    catch(e){return[]}
  }

  function ensureNav(){
    const nav=$('.nav');
    if(!nav)return;
    if(!nav.querySelector('a[href="#latest"]')){
      const a=document.createElement('a');
      a.href='#latest';
      a.dataset.enhanceCopy='navLatest';
      a.textContent=t('navLatest');
      const timeline=nav.querySelector('a[href="#timeline"]');
      nav.insertBefore(a,timeline||nav.firstChild);
    }
    if(!nav.querySelector('a[href="#coauthor-graph"]')){
      const a=document.createElement('a');
      a.href='#coauthor-graph';
      a.dataset.enhanceCopy='navGraph';
      a.textContent=t('navGraph');
      const library=nav.querySelector('a[href="#library"]');
      nav.insertBefore(a,library||null);
    }
  }

  function makeHead(id,eyebrow,title,subtitle){
    const h=document.createElement('section');
    h.className='section-head spacious enhancement-head';
    h.id=id;
    h.innerHTML=`<div><p class="eyebrow small" data-enhance-copy="${eyebrow}">${esc(t(eyebrow))}</p><h2 data-enhance-copy="${title}">${esc(t(title))}</h2><p data-enhance-copy="${subtitle}">${esc(t(subtitle))}</p></div>`;
    return h;
  }

  function ensureSections(){
    if(!$('#latest')){
      const head=makeHead('latest','latestEyebrow','latestTitle','latestSubtitle');
      const body=document.createElement('section');
      body.className='latest-additions';
      body.innerHTML='<div id="latestGrid" class="latest-grid"></div>';
      const roadmap=$('#roadmap');
      if(roadmap){roadmap.insertAdjacentElement('afterend',body);roadmap.insertAdjacentElement('afterend',head)}
      else{document.querySelector('main')?.prepend(body);document.querySelector('main')?.prepend(head)}
    }
    if(!$('#coauthor-graph')){
      const head=makeHead('coauthor-graph','graphEyebrow','graphTitle','graphSubtitle');
      const body=document.createElement('section');
      body.className='coauthor-graph-shell';
      body.innerHTML=`
        <p class="graph-hint" data-enhance-copy="graphHint">${esc(t('graphHint'))}</p>
        <div class="coauthor-layout">
          <div class="coauthor-stage">
            <svg id="coauthorSvg" role="img" aria-label="Paper co-author graph"></svg>
            <div id="yearLegend" class="year-legend" aria-label="Year legend"></div>
          </div>
          <aside id="graphInfo" class="graph-info"></aside>
        </div>`;
      const topicMap=$('#topicMap');
      if(topicMap){topicMap.insertAdjacentElement('afterend',body);topicMap.insertAdjacentElement('afterend',head)}
      else{const lib=$('#library');lib?.insertAdjacentElement('beforebegin',body);lib?.insertAdjacentElement('beforebegin',head)}
    }
  }

  function latestCard(p){
    const date=dateKey(p);
    const stamp=date?`${t('latestStamp')} ${esc(date)}`:`${t('published')} ${esc(yearOf(p))}`;
    const topicTags=topics(p).map(x=>`<span class="tag">${esc(x)}</span>`).join('');
    return `<article class="latest-card">
      <div class="latest-top"><span class="latest-stamp">${stamp}</span><span class="year-pill">${esc(yearOf(p))}</span></div>
      <h3>${esc(p.title||'Untitled')}</h3>
      <p class="meta">${esc(p.authors||'')}</p>
      <p class="meta">${esc(p.venue||p.venue_group||'')}</p>
      <div class="tags">${topicTags}</div>
      <div class="links"><a href="paper.html?id=${encodeURIComponent(p.id)}">${esc(t('details'))}</a>${p.primary_url?`<a href="${esc(p.primary_url)}" target="_blank" rel="noopener">Publisher</a>`:''}${p.pdf_url?`<a href="${esc(p.pdf_url)}" target="_blank" rel="noopener">PDF</a>`:''}</div>
    </article>`;
  }

  function renderLatest(){
    const grid=$('#latestGrid');
    if(!grid)return;
    const latest=papers.slice().sort((a,b)=>dateKey(b).localeCompare(dateKey(a))||publicationKey(b).localeCompare(publicationKey(a))).slice(0,6);
    grid.innerHTML=latest.map(latestCard).join('');
  }

  function normalizeAuthor(name){
    return String(name||'')
      .normalize('NFKD')
      .replace(/[\u0300-\u036f]/g,'')
      .replace(/\bet\s+al\.?/gi,'')
      .replace(/[^a-z0-9]+/gi,' ')
      .trim()
      .toLowerCase();
  }
  function parseAuthors(str){
    const seen=new Map();
    String(str||'').split(';').map(a=>a.trim()).filter(Boolean).forEach(name=>{
      if(/^(et\s+al\.?|others)$/i.test(name))return;
      if(/\bet\s+al\.?$/i.test(name))name=name.replace(/\bet\s+al\.?$/i,'').trim();
      const key=normalizeAuthor(name);
      if(key&&key.length>2&&!seen.has(key))seen.set(key,{name,key});
    });
    return Array.from(seen.values());
  }
  function colorForYear(year,years){
    const i=Math.max(0,years.indexOf(year));
    const hue=(i*47+205)%360;
    return `hsl(${hue} 58% 44%)`;
  }
  function buildGraph(){
    const nodes=papers.map((p,i)=>({idx:i,id:p.id,p,year:yearOf(p),authors:parseAuthors(p.authors),x:0,y:0,vx:0,vy:0}));
    nodes.forEach(n=>n.authorSet=new Set(n.authors.map(a=>a.key)));
    const links=[];
    for(let i=0;i<nodes.length;i++){
      for(let j=i+1;j<nodes.length;j++){
        const shared=nodes[i].authors.filter(a=>nodes[j].authorSet.has(a.key)).map(a=>a.name);
        if(shared.length)links.push({source:i,target:j,shared});
      }
    }
    return {nodes,links,years:Array.from(new Set(nodes.map(n=>n.year))).sort((a,b)=>b.localeCompare(a))};
  }
  function layoutGraph(g,w,h){
    const nodes=g.nodes,links=g.links,years=g.years;
    const n=Math.max(1,nodes.length);
    const cx=w/2,cy=h/2;
    nodes.forEach((node,i)=>{
      const yr=Math.max(0,years.indexOf(node.year));
      const band=years.length>1?(yr/(years.length-1)-.5)*w*.58:0;
      const angle=(Math.PI*2*i/n)-Math.PI/2;
      node.x=cx+Math.cos(angle)*w*.22+band*.25;
      node.y=cy+Math.sin(angle)*h*.28;
      node.vx=0;node.vy=0;
    });
    for(let iter=0;iter<260;iter++){
      for(let i=0;i<nodes.length;i++){
        for(let j=i+1;j<nodes.length;j++){
          const a=nodes[i],b=nodes[j];
          let dx=a.x-b.x,dy=a.y-b.y;
          let d2=dx*dx+dy*dy+.01;
          const f=Math.min(4,760/d2);
          const d=Math.sqrt(d2);
          dx/=d;dy/=d;
          a.vx+=dx*f;b.vx-=dx*f;a.vy+=dy*f;b.vy-=dy*f;
        }
      }
      links.forEach(l=>{
        const a=nodes[l.source],b=nodes[l.target];
        let dx=b.x-a.x,dy=b.y-a.y;
        const d=Math.sqrt(dx*dx+dy*dy)||1;
        const target=86+Math.min(70,l.shared.length*12);
        const f=(d-target)*.018;
        dx/=d;dy/=d;
        a.vx+=dx*f;b.vx-=dx*f;a.vy+=dy*f;b.vy-=dy*f;
      });
      nodes.forEach(node=>{
        const yr=Math.max(0,years.indexOf(node.year));
        const tx=cx+(years.length>1?(yr/(years.length-1)-.5)*w*.52:0);
        node.vx+=(tx-node.x)*.004+(cx-node.x)*.002;
        node.vy+=(cy-node.y)*.003;
        node.vx*=.78;node.vy*=.78;
        node.x=Math.max(30,Math.min(w-30,node.x+node.vx));
        node.y=Math.max(30,Math.min(h-30,node.y+node.vy));
      });
    }
  }

  function renderLegend(){
    const el=$('#yearLegend');
    if(!el||!graph)return;
    el.innerHTML=`<span class="legend-label">${esc(t('legend'))}</span>`+graph.years.map(y=>`<span class="legend-item"><i style="background:${colorForYear(y,graph.years)}"></i>${esc(y)}</span>`).join('');
  }
  function selectedLinks(){
    if(!graph||activeNode<0)return[];
    return graph.links.filter(l=>l.source===activeNode||l.target===activeNode);
  }
  function renderGraphInfo(){
    const panel=$('#graphInfo');
    if(!panel||!graph)return;
    if(activeNode<0){
      panel.innerHTML=`<h3>${esc(t('graphStats'))}</h3><p class="graph-idle">${esc(t('graphIdle'))}</p><div class="graph-stat-grid"><b>${graph.nodes.length}</b><span>${esc(t('papers'))}</span><b>${graph.links.length}</b><span>${esc(t('edges'))}</span><b>${graph.years.length}</b><span>${esc(t('years'))}</span></div>`;
      return;
    }
    const n=graph.nodes[activeNode],p=n.p,links=selectedLinks();
    const linkRows=links.slice(0,8).map(l=>{
      const other=graph.nodes[l.source===activeNode?l.target:l.source];
      return `<li><a href="paper.html?id=${encodeURIComponent(other.id)}">${esc(other.p.title)}</a><small>${esc(t('sharedAuthors'))}: ${esc(l.shared.join(', '))}</small></li>`;
    }).join('');
    panel.innerHTML=`<h3>${esc(t('selectedPaper'))}</h3>
      <p class="graph-paper-title">${esc(p.title||'Untitled')}</p>
      <dl class="graph-meta"><dt>${lang()==='zh'?'作者':'Authors'}</dt><dd>${esc(p.authors||'')}</dd><dt>${lang()==='zh'?'期刊 / 会议':'Venue'}</dt><dd>${esc(p.venue||p.venue_group||'')}</dd><dt>${lang()==='zh'?'年份':'Year'}</dt><dd>${esc(yearOf(p))}</dd></dl>
      <a class="graph-detail" href="paper.html?id=${encodeURIComponent(p.id)}">${esc(t('openDetails'))}</a>
      <h4>${esc(t('sharedWith'))}</h4>
      ${links.length?`<ul class="connection-list">${linkRows}</ul>`:`<p class="graph-idle">${esc(t('noShared'))}</p>`}`;
  }
  function renderGraph(){
    const svg=$('#coauthorSvg');
    if(!svg||!papers.length)return;
    graph=buildGraph();
    activeNode=Math.min(activeNode,graph.nodes.length-1);
    const width=Math.max(720,Math.round(svg.getBoundingClientRect().width||900));
    const height=Math.max(430,Math.min(620,Math.round(width*.62)));
    svg.setAttribute('viewBox',`0 0 ${width} ${height}`);
    svg.setAttribute('height',String(height));
    layoutGraph(graph,width,height);
    const selected=new Set();
    selectedLinks().forEach(l=>{selected.add(l.source);selected.add(l.target)});
    const edgeHtml=graph.links.map((l,i)=>{
      const a=graph.nodes[l.source],b=graph.nodes[l.target];
      const on=activeNode<0||l.source===activeNode||l.target===activeNode;
      return `<line class="co-edge" data-link="${i}" x1="${a.x.toFixed(1)}" y1="${a.y.toFixed(1)}" x2="${b.x.toFixed(1)}" y2="${b.y.toFixed(1)}" opacity="${on?'.58':'.06'}"><title>${esc(l.shared.join(', '))}</title></line>`;
    }).join('');
    const nodeHtml=graph.nodes.map(n=>{
      const isActive=n.idx===activeNode;
      const isNear=activeNode<0||selected.has(n.idx)||isActive;
      const r=7+Math.min(8,Math.sqrt(n.authors.length)*2.3);
      const label=String(n.p.title||'').slice(0,46);
      return `<g class="co-node ${isActive?'selected':''}" data-node="${n.idx}" tabindex="0" role="button" aria-label="${esc(n.p.title)}" transform="translate(${n.x.toFixed(1)} ${n.y.toFixed(1)})" opacity="${isNear?'1':'.24'}">
        <circle r="${r.toFixed(1)}" fill="${colorForYear(n.year,graph.years)}"></circle>
        <text y="${-(r+7).toFixed(1)}">${esc(label)}</text>
        <title>${esc(n.p.title)} · ${esc(n.p.authors||'')} · ${esc(n.p.venue||'')} · ${esc(n.year)}</title>
      </g>`;
    }).join('');
    svg.innerHTML=`<g class="co-edges">${edgeHtml}</g><g class="co-nodes">${nodeHtml}</g>`;
    $$('.co-node').forEach(el=>{
      const pick=()=>{activeNode=Number(el.dataset.node);renderGraph();};
      el.addEventListener('click',pick);
      el.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();pick();}});
    });
    renderLegend();
    renderGraphInfo();
  }

  function applyCopy(){
    $$('[data-enhance-copy]').forEach(el=>{el.textContent=t(el.dataset.enhanceCopy)});
    renderLatest();
    renderGraphInfo();
  }

  async function init(){
    ensureNav();
    ensureSections();
    const focus=await load('data/focus_papers.json');
    const base=await load('data/papers.json');
    papers=uniq([...focus,...base]).sort((a,b)=>publicationKey(b).localeCompare(publicationKey(a))||String(b.year||'').localeCompare(String(a.year||'')));
    renderLatest();
    renderGraph();
    applyCopy();
    $$('.lang button').forEach(b=>b.addEventListener('click',()=>setTimeout(applyCopy,0)));
    window.addEventListener('resize',()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(renderGraph,180)});
  }

  document.addEventListener('DOMContentLoaded',init);
})();
