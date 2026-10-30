// Navigation is a view preference: never dispatch an editor transaction here.
export function createDocumentOutline({editor,body,rail,toggle}){
 const scroll=editor.view.dom.closest('.rich-editor-scroll'),doc=editor.view.dom;
 rail.setAttribute('aria-label','文档目录');rail.innerHTML='<div class="outline-heading"><strong>目录</strong><button type="button" class="icon-button outline-close" aria-label="收起目录">'+window.WorkmoireIcons.render('close')+'</button></div><nav class="outline-navigation" aria-label="章节导航"><ol></ol></nav><p class="outline-empty">将段落设为标题 1–6，目录会自动显示。</p>';
 const nav=rail.querySelector('nav'),list=rail.querySelector('ol'),empty=rail.querySelector('.outline-empty'),close=rail.querySelector('.outline-close');
 let entries=[],positions=[],active=-1,compact=false,expanded=false,collapsed=false,destroyed=false,refreshTimer=0,geometryFrame=0,scrollFrame=0;
 const cleanup=[];
 const listen=(target,type,handler,options)=>{target.addEventListener(type,handler,options);cleanup.push(()=>target.removeEventListener(type,handler,options));};
 function setActive(index){
  if(index===active)return;
  entries[active]?.button.removeAttribute('aria-current');active=index;
  entries[active]?.button.setAttribute('aria-current','location');revealActive();
 }
 function revealActive(){
  if(compact&&!expanded)return;const button=entries[active]?.button;if(!button)return;
  const rect=button.getBoundingClientRect(),bounds=nav.getBoundingClientRect();
  if(rect.top<bounds.top)nav.scrollTop-=bounds.top-rect.top+8;else if(rect.bottom>bounds.bottom)nav.scrollTop+=rect.bottom-bounds.bottom+8;
 }
 function updateActive(){
  scrollFrame=0;if(destroyed||!positions.length)return;
  if(scroll.scrollHeight>scroll.clientHeight+1&&scroll.scrollHeight-scroll.clientHeight-scroll.scrollTop<3){setActive(positions.at(-1).index);return;}
  const target=scroll.scrollTop+28;let left=0,right=positions.length-1;
  while(left<right){const mid=Math.ceil((left+right)/2);if(positions[mid].top<=target)left=mid;else right=mid-1;}
  setActive(positions[left].index);
 }
 function geometry(){
  geometryFrame=0;if(destroyed)return;
  const top=scroll.getBoundingClientRect().top;
  positions=entries.flatMap((entry,index)=>{const node=editor.view.nodeDOM(entry.pos);return node instanceof HTMLElement?[{index,top:node.getBoundingClientRect().top-top+scroll.scrollTop}]:[];}).sort((a,b)=>a.top-b.top||a.index-b.index);
  updateActive();revealActive();
 }
 function scheduleGeometry(){if(!geometryFrame&&!destroyed)geometryFrame=requestAnimationFrame(geometry);}
 function refresh(){
  clearTimeout(refreshTimer);refreshTimer=0;if(destroyed)return;
  const headings=editor.outline(),base=Math.min(...headings.map(h=>h.level),6);
  for(let index=0;index<headings.length;index++){
   const heading=headings[index];let entry=entries[index];
   if(!entry){const li=document.createElement('li'),button=document.createElement('button');button.type='button';button.dataset.outlineIndex=String(index);li.append(button);list.append(li);entry={li,button};entries.push(entry);}
   entry.pos=heading.pos;const title=heading.title.trim()||'未命名标题';
   if(entry.button.textContent!==title)entry.button.textContent=title;
   entry.button.title=title;entry.button.dataset.level=String(heading.level);entry.button.style.setProperty('--outline-indent',String((heading.level-base)*12)+'px');
  }
  while(entries.length>headings.length)entries.pop().li.remove();
  if(active>=entries.length)active=-1;
  empty.hidden=entries.length>0;nav.hidden=!entries.length;scheduleGeometry();
 }
 function update(){clearTimeout(refreshTimer);refreshTimer=setTimeout(refresh,120);}
 function setExpanded(value,returnFocus=false){
  const collapsible=compact||document.body.classList.contains('focus-mode');expanded=collapsible?Boolean(value):true;collapsed=collapsible&&!expanded;body.dataset.outlineOpen=String(expanded);body.dataset.outlineCollapsed=String(collapsed);toggle.hidden=!collapsible;toggle.setAttribute('aria-expanded',String(expanded));toggle.title=collapsed?'展开目录':'收起目录';toggle.setAttribute('aria-label',collapsed?'展开文档目录':'收起文档目录');
  rail.inert=collapsible&&!expanded;rail.setAttribute('aria-hidden',String(collapsible&&!expanded));
  if(returnFocus&&collapsible)toggle.focus({preventScroll:true});
  if(expanded)scheduleGeometry();
 }
 function resize(){
  if(destroyed)return;
  const next=body.clientWidth<760;
  if(next!==compact){compact=next;expanded=false;}
  body.dataset.outlineCompact=String(compact);toggle.hidden=!compact;setExpanded(expanded);scheduleGeometry();
 }
 listen(toggle,'click',()=>setExpanded(!expanded));listen(close,'click',()=>setExpanded(false,true));
 listen(list,'click',event=>{
  const button=event.target.closest('[data-outline-index]');if(!button)return;
  refresh();geometry();const index=Number(button.dataset.outlineIndex),position=positions.find(p=>p.index===index);if(!position)return;
  const keyboard=event.detail===0;setExpanded(false,keyboard);
  scroll.scrollTo({top:Math.max(0,position.top-24),behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});setActive(index);
 });
 listen(scroll,'scroll',()=>{if(!scrollFrame)scrollFrame=requestAnimationFrame(updateActive);},{passive:true});
 listen(document,'pointerdown',event=>{if(compact&&expanded&&!rail.contains(event.target)&&!toggle.contains(event.target))setExpanded(false);});
 listen(document,'keydown',event=>{if(event.key==='Escape'&&compact&&expanded&&!event.isComposing){event.preventDefault();event.stopPropagation();setExpanded(false,true);}},{capture:true});
 editor.tiptap.on('update',update);cleanup.push(()=>editor.tiptap.off('update',update));
 const layout=new ResizeObserver(resize);layout.observe(body);
 const content=new ResizeObserver(scheduleGeometry);content.observe(doc);content.observe(scroll);
 const appearance=new MutationObserver(scheduleGeometry);appearance.observe(doc,{attributes:true,attributeFilter:['data-body-font']});
 refresh();resize();
 return {refresh,resize,collapse(value){setExpanded(!value,true);},destroy(){destroyed=true;clearTimeout(refreshTimer);cancelAnimationFrame(geometryFrame);cancelAnimationFrame(scrollFrame);layout.disconnect();content.disconnect();appearance.disconnect();cleanup.forEach(fn=>fn());entries=[];positions=[];}};
}
