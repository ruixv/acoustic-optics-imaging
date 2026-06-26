(()=>{
  const REPLACEMENTS=[
    [/Paper co-author graph/g,'Paper Graph'],
    [/co-author links/g,'links'],
    [/co-author link/g,'link'],
    [/co-author edge/g,'link'],
    [/co-author connections/g,'connections'],
    [/co-author connection/g,'connection'],
    [/Co-author links/g,'Paper links'],
    [/Selected co-author edge/g,'Selected link'],
    [/论文共同作者关系图/g,'论文关系图'],
    [/共同作者连边/g,'连接'],
    [/共同作者连接/g,'连接']
  ];
  function cleanTextNode(node){
    let text=node.nodeValue, next=text;
    REPLACEMENTS.forEach(([re,to])=>{next=next.replace(re,to)});
    if(next!==text)node.nodeValue=next;
  }
  function clean(root=document.body){
    if(!root)return;
    const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT,{acceptNode:n=>n.nodeValue&&/co-author|共同作者|Paper co-author/.test(n.nodeValue)?NodeFilter.FILTER_ACCEPT:NodeFilter.FILTER_REJECT});
    const nodes=[];
    while(walker.nextNode())nodes.push(walker.currentNode);
    nodes.forEach(cleanTextNode);
    document.querySelectorAll('[aria-label]').forEach(el=>{
      let v=el.getAttribute('aria-label')||'', next=v;
      REPLACEMENTS.forEach(([re,to])=>{next=next.replace(re,to)});
      if(next!==v)el.setAttribute('aria-label',next);
    });
  }
  document.addEventListener('DOMContentLoaded',()=>{
    clean();
    new MutationObserver(m=>m.forEach(x=>x.addedNodes.forEach(n=>{if(n.nodeType===1)clean(n);else if(n.nodeType===3)cleanTextNode(n)}))).observe(document.body,{childList:true,subtree:true});
  });
})();
