import {pdfSource,pdfCitation,pdfViewerURL,pdfFragment,parsePDFAnchor} from './pdf-source.js';

export function createPaperDesk({root,editor,getItem,toggle,getFocus,setFocus,setWrite,copy,notify,save,capture}){
 const layout=root.querySelector('.document-content-layout'),writing=root.querySelector('.writing-area'),scroll=editor.view.dom.closest('.rich-editor-scroll');
 const pane=document.createElement('section');pane.className='paper-source-pane';pane.setAttribute('aria-label','论文原文');pane.hidden=true;
 pane.innerHTML='<div class="paper-source-heading"><span>原文</span><select aria-label="选择论文 PDF"></select><span class="paper-source-caption"></span></div><div class="paper-source-view"><p class="paper-source-empty">在正文中插入已上传的 PDF 后，可在这里阅读。</p></div>';
 const separator=document.createElement('button');separator.type='button';separator.className='paper-desk-separator';separator.setAttribute('role','separator');separator.setAttribute('aria-label','调整原文与笔记宽度');separator.setAttribute('aria-orientation','vertical');separator.setAttribute('aria-valuemin','35');separator.setAttribute('aria-valuemax','70');separator.hidden=true;
 const tabs=document.createElement('div');tabs.className='paper-desk-tabs';tabs.hidden=true;tabs.setAttribute('aria-label','阅读台视图');tabs.innerHTML='<button type="button" data-desk-tab="source">原文</button><button type="button" data-desk-tab="notes">笔记</button>';
 root.insertBefore(tabs,layout);layout.prepend(pane,separator);
 const select=pane.querySelector('select'),caption=pane.querySelector('.paper-source-caption'),viewerHost=pane.querySelector('.paper-source-view'),empty=pane.querySelector('.paper-source-empty'),narrow=matchMedia('(max-width:760px)');
 const cleanups=[];let sources=[],records=[],frame=null,selected=null,active=false,previousFocus=false,ratio=55,mobile='source',destroyed=false,frameRequest=0,scanTimer=0,storeTimer=0,drag=null,anchor=null;
 const listen=(target,name,fn,options)=>{target.addEventListener(name,fn,options);cleanups.push(()=>target.removeEventListener(name,fn,options));};
 const key=()=>getItem()?.id?'workmoire:reading-desk:'+getItem().id:null;
 let preference=null;try{if(key())preference=JSON.parse(localStorage.getItem(key())||'null');}catch{}
 if(Number.isFinite(preference?.ratio))ratio=Math.max(35,Math.min(70,preference.ratio));
 function noteAnchor(){
  const top=scroll.getBoundingClientRect().top;let result=null;
  editor.tiptap.state.doc.forEach((node,pos)=>{if(result)return;const dom=editor.view.nodeDOM(pos);if(dom instanceof HTMLElement&&dom.getBoundingClientRect().bottom>top+1)result={pos,offset:dom.getBoundingClientRect().top-top};});
  return result||{pos:0,offset:0};
 }
 function restoreNotes(value){
  if(destroyed||editor.tiptap.isDestroyed||!value||!Number.isInteger(value.pos)||!Number.isFinite(value.offset))return;
  const dom=editor.view.nodeDOM(Math.max(0,Math.min(value.pos,editor.tiptap.state.doc.content.size)));
  if(dom instanceof HTMLElement)scroll.scrollTop+=dom.getBoundingClientRect().top-scroll.getBoundingClientRect().top-value.offset;
 }
 function saveView(){
  clearTimeout(storeTimer);if(destroyed||!key())return;
  if(active&&(!narrow.matches||mobile==='notes'))anchor=noteAnchor();
  try{localStorage.setItem(key(),JSON.stringify({active,ratio,source:selected?.path,notes:anchor,revision:getItem().updated_at,mobile}));}catch{}
 }
 function scheduleSave(){clearTimeout(storeTimer);storeTimer=setTimeout(saveView,180);}
 function updateRatio(){layout.style.setProperty('--paper-source-ratio',ratio+'%');separator.setAttribute('aria-valuenow',String(Math.round(ratio)));separator.setAttribute('aria-valuetext','原文 '+Math.round(ratio)+'%，笔记 '+Math.round(100-ratio)+'%');}
 function updateMobile(){
  root.dataset.deskTab=mobile;tabs.hidden=!active||!narrow.matches;
  for(const button of tabs.querySelectorAll('button'))button.setAttribute('aria-pressed',String(button.dataset.deskTab===mobile));
  pane.inert=active&&narrow.matches&&mobile!=='source';writing.inert=active&&narrow.matches&&mobile!=='notes';
 }
 function changeTab(value){if(mobile==='notes'&&active)anchor=noteAnchor();mobile=value;updateMobile();if(value==='notes')requestAnimationFrame(()=>restoreNotes(anchor));scheduleSave();}
 function sourceFromNode(node,pos,result){
  if(node.type.name==='pdf'){
   const source=pdfSource(node.attrs.src,{shared:false});if(source)result.push({...source,pos,primary:true,title:node.attrs.title&&node.attrs.title!=='PDF 原文'?node.attrs.title:getItem()?.title||'PDF 原文'});
  }
  for(const mark of node.marks||[]){if(mark.type.name==='link'){const source=pdfCitation(mark.attrs.href),label=node.textContent.match(/^(.+) · 第 [0-9–]+ 页$/);if(source?.privateFile)result.push({...source,pos,title:label?label[1].slice(0,200):'引用来源 PDF'});}}
 }
 function scan(){
  clearTimeout(scanTimer);if(destroyed)return;const next=[];editor.tiptap.state.doc.descendants((node,pos)=>sourceFromNode(node,pos,next));records=next;
  const unique=new Map();for(const source of next)if(!unique.has(source.path)||source.primary)unique.set(source.path,source);sources=[...unique.values()];
  const current=selected&&sources.find(s=>s.path===selected.path);selected=current||sources.find(s=>s.path===preference?.source)||sources[0]||null;
  select.replaceChildren(...sources.map((source,index)=>{const option=document.createElement('option');option.value=source.path;option.textContent=sources.length>1?(index+1)+'. '+source.title:source.title;return option;}));
  select.hidden=sources.length<=1;caption.hidden=sources.length>1;caption.textContent=selected?.title||'暂无 PDF';caption.title=caption.textContent;select.value=selected?.path||'';
  toggle.hidden=!sources.length&&!active;
  if(active)showSource();
 }
 function showSource(page=null){
  if(!selected){frame?.contentWindow?.WorkmoirePDF?.save();frame?.remove();frame=null;empty.hidden=false;return;}
  empty.hidden=true;
  if(frame?.dataset.source!==selected.path){
   frame?.contentWindow?.WorkmoirePDF?.save();frame?.remove();frame=document.createElement('iframe');frame.className='paper-desk-pdf';frame.title='阅读台 PDF 原文';frame.referrerPolicy='no-referrer';frame.dataset.source=selected.path;
   frame.src=pdfViewerURL(selected,page,true);viewerHost.append(frame);
  }else if(page){
   const api=frame.contentWindow?.WorkmoirePDF;if(api)api.navigate(page);else frame.src=pdfViewerURL(selected,page,true);
  }
 }
 function setActive(value,page=null){
  if(destroyed||value===active)return;if(value&&!selected)return;
  if(value){
   anchor=noteAnchor();previousFocus=getFocus();active=true;document.body.classList.add('paper-desk-mode');root.classList.add('paper-desk');pane.hidden=false;separator.hidden=false;setFocus(true);updateRatio();updateMobile();showSource(page);
   requestAnimationFrame(()=>restoreNotes(anchor));
  }else{
   if(drag)finishDrag(false);anchor=noteAnchor();active=false;document.body.classList.remove('paper-desk-mode');root.classList.remove('paper-desk');pane.hidden=true;separator.hidden=true;tabs.hidden=true;pane.inert=false;writing.inert=false;setFocus(previousFocus);requestAnimationFrame(()=>restoreNotes(anchor));
  }
  toggle.setAttribute('aria-pressed',String(active));toggle.setAttribute('aria-label',active?'退出论文阅读台':'打开论文阅读台');toggle.title=active?'退出论文阅读台 · Esc':'打开论文阅读台';toggle.querySelector('span').textContent=active?'退出阅读台':'阅读台';saveView();
 }
 function openCitation(citation){
  if(!citation.privateFile)return false;const known=sources.find(s=>s.path===citation.path);
  selected=known||{...citation,title:'引用来源 PDF'};toggle.hidden=false;
  if(!active)setActive(true,citation);else showSource(citation);if(narrow.matches)changeTab('source');return true;
 }
 function onUpdate({transaction}){
  let changedSource=false;
  for(const step of transaction.steps)step.slice?.content.descendants(node=>{const found=[];sourceFromNode(node,0,found);if(found.length)changedSource=true;});
  records=records.map(record=>{const pos=transaction.mapping.map(record.pos),node=transaction.doc.nodeAt(pos),found=[];if(node)sourceFromNode(node,pos,found);if(!found.some(item=>item.path===record.path))changedSource=true;return {...record,pos};});
  if(changedSource){clearTimeout(scanTimer);scanTimer=setTimeout(scan,60);}
 }
 function finishDrag(commit){
  if(!drag)return;const original=drag;drag=null;if(!commit)ratio=original.ratio;
  root.classList.remove('paper-desk-resizing');if(separator.hasPointerCapture(original.id))separator.releasePointerCapture(original.id);updateRatio();restoreNotes(original.anchor);scheduleSave();
 }
 listen(separator,'pointerdown',event=>{if(event.button!==0)return;event.preventDefault();drag={id:event.pointerId,ratio,anchor:noteAnchor()};separator.setPointerCapture(event.pointerId);root.classList.add('paper-desk-resizing');});
 listen(separator,'pointermove',event=>{if(!drag)return;const rect=layout.getBoundingClientRect();ratio=Math.max(35,Math.min(70,100*(event.clientX-rect.left)/rect.width));updateRatio();});
 listen(separator,'pointerup',()=>finishDrag(true));listen(separator,'pointercancel',()=>finishDrag(false));listen(separator,'lostpointercapture',()=>finishDrag(false));
 listen(separator,'keydown',event=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;event.preventDefault();const before=noteAnchor();ratio=event.key==='Home'?35:event.key==='End'?70:Math.max(35,Math.min(70,ratio+(event.key==='ArrowRight'?2:-2)));updateRatio();requestAnimationFrame(()=>restoreNotes(before));scheduleSave();});
 listen(toggle,'mousedown',event=>event.preventDefault());listen(toggle,'click',()=>setActive(!active));
 listen(select,'change',()=>{selected=sources.find(s=>s.path===select.value)||null;showSource();scheduleSave();});
 listen(tabs,'click',event=>{const button=event.target.closest('[data-desk-tab]');if(button)changeTab(button.dataset.deskTab);});
 listen(narrow,'change',()=>{updateMobile();if(active)requestAnimationFrame(()=>restoreNotes(anchor));});
 listen(scroll,'scroll',scheduleSave,{passive:true});listen(window,'pagehide',saveView);
 let capturePending=false;const captureIds=new Set();
 listen(window,'message',async event=>{
  const data=event.data;if(!active||!frame||event.origin!==location.origin||event.source!==frame.contentWindow||!data||data.source!==selected?.path)return;
  if(data.type==='workmoire:pdf-command'){
   if(document.querySelector('dialog[open]'))return;
   if(data.action==='save')save?.();
   if(data.action==='notes'){if(narrow.matches)changeTab('notes');if(editor.tiptap.isEditable)editor.focus();else{scroll.tabIndex=-1;scroll.focus({preventScroll:true});}}
   if(data.action==='exit')document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true}));
   return;
  }
  if(data.type==='workmoire:pdf-capture'){
   const target=frame,anchor=parsePDFAnchor(pdfFragment(data));
   if(capturePending||typeof data.requestId!=='string'||!/^crop-[0-9]+-[0-9]+$/.test(data.requestId)||captureIds.has(data.requestId)||!anchor?.rects||anchor.rects.length!==1||!(data.blob instanceof Blob)||data.blob.type!=='image/png'||data.blob.size>12*1024*1024)return;
   capturePending=true;captureIds.add(data.requestId);if(captureIds.size>32)captureIds.delete(captureIds.values().next().value);let ok=false;
   try{setWrite();if(narrow.matches)changeTab('notes');ok=Boolean(await capture?.({...data,...anchor,source:selected.src,title:selected.title||'PDF 原文'}));}catch(error){notify(error.message||'截图插入失败，请重试。',true);}finally{capturePending=false;if(!destroyed&&target.isConnected)target.contentWindow.postMessage({type:'workmoire:pdf-capture-result',requestId:data.requestId,ok},location.origin);}
   return;
  }
  if(data.type!=='workmoire:pdf-quote'||!parsePDFAnchor(pdfFragment(data)))return;
  if(typeof data.text!=='string'||!data.text.trim()||data.text.length>12000||!Number.isInteger(data.page)||data.page<1||data.page>10000||!Number.isInteger(data.endPage)||data.endPage<data.page||data.endPage>10000)return;
  const source=selected.src,pages=data.endPage>data.page?data.page+'–'+data.endPage:String(data.page),title=selected.title||'PDF 原文';
  if(data.action==='copy'){
   const escape=value=>value.replace(/([\\`*_[\]<>])/g,'\\$1');copy(data.text.trim().split(/\n/).map(line=>'> '+escape(line)).join('\n')+'\n\n['+escape(title)+' · 第 '+pages+' 页]('+source+pdfFragment(data)+')');return;
  }
  if(data.action!=='insert')return;
  if(editor.isComposing()){notify('请先完成中文输入，再插入引用。',true);return;}
  setWrite();if(narrow.matches)changeTab('notes');
  if(editor.insertPDFQuote({...data,source,title}))notify('已引用到笔记，保存后生效。');
 });
 listen(document,'keydown',event=>{
  if(active&&!event.isComposing&&(event.ctrlKey||event.metaKey)&&event.shiftKey&&event.key==='Enter'&&!document.querySelector('dialog[open]')){event.preventDefault();event.stopImmediatePropagation();if(narrow.matches)changeTab('source');frame?.focus();frame?.contentWindow?.document.querySelector('#pdf-container')?.focus();return;}
  if(event.key!=='Escape'||event.isComposing||!active)return;
  if(drag){event.preventDefault();event.stopImmediatePropagation();finishDrag(false);return;}
  if(document.querySelector('dialog[open],.insert-menu[open],.save-options-menu:not([hidden]),.document-body[data-outline-open="true"][data-outline-compact="true"]'))return;
  event.preventDefault();event.stopImmediatePropagation();setActive(false);toggle.focus({preventScroll:true});
 },{capture:true});
 editor.tiptap.on('update',onUpdate);cleanups.push(()=>editor.tiptap.off('update',onUpdate));scan();
 if(preference?.active&&selected){frameRequest=requestAnimationFrame(()=>{frameRequest=0;if(destroyed)return;setActive(true);if(preference.revision===getItem().updated_at&&preference.notes){anchor=preference.notes;requestAnimationFrame(()=>restoreNotes(anchor));}if(preference.mobile==='notes')changeTab('notes');});}
 return {openCitation,isActive:()=>active,destroy(){if(destroyed)return;saveView();frame?.contentWindow?.WorkmoirePDF?.save();if(active){document.body.classList.remove('paper-desk-mode');root.classList.remove('paper-desk');writing.inert=false;setFocus(previousFocus);}destroyed=true;clearTimeout(scanTimer);clearTimeout(storeTimer);cancelAnimationFrame(frameRequest);cleanups.forEach(fn=>fn());frame?.remove();pane.remove();separator.remove();tabs.remove();}};
}
