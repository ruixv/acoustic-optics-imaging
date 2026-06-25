
const q=document.getElementById('q'), venue=document.getElementById('venue'), topic=document.getElementById('topic'), rel=document.getElementById('rel');
function apply(){
  const qq=(q.value||'').toLowerCase(); const vv=venue.value; const tt=topic.value; const rr=rel.value;
  document.querySelectorAll('.card').forEach(c=>{
    const text=c.dataset.text; const okq=!qq||text.includes(qq); const okv=!vv||c.dataset.venue===vv; const okt=!tt||c.dataset.topics.includes(tt); const okr=!rr||c.dataset.rel===rr;
    c.style.display=(okq&&okv&&okt&&okr)?'flex':'none';
  });
}
[q,venue,topic,rel].forEach(x=>x.addEventListener('input',apply));
