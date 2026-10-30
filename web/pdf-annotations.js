import {parsePDFAnchor,pdfFragment} from './pdf-source.js';

export function normalizedRectangle(rect,page){
 const x=Math.max(0,Math.floor((rect.left-page.left)/page.width*10000)),y=Math.max(0,Math.floor((rect.top-page.top)/page.height*10000));
 const right=Math.min(10000,Math.ceil((rect.right-page.left)/page.width*10000)),bottom=Math.min(10000,Math.ceil((rect.bottom-page.top)/page.height*10000));
 return right>x&&bottom>y?[x,y,right-x,bottom-y]:null;
}
export function textAnchor(range,page,fingerprint){
 const bounds=page.getBoundingClientRect(),seen=new Set(),rects=[];
 for(const rect of range.getClientRects()){
  const normalized=normalizedRectangle(rect,bounds);if(!normalized||rect.width<.5||rect.height<.5)continue;
  const key=normalized.join(',');if(seen.has(key))continue;seen.add(key);rects.push(normalized);if(rects.length===32)break;
 }
 return rects.length?{rects,fingerprint}:{};
}
export function citationHighlighter({viewer,eventBus,fingerprint,notice}){
 let pending=null,frame=0,timer=0,marks=[];
 function clear(){clearTimeout(timer);cancelAnimationFrame(frame);marks.forEach(el=>el.remove());marks=[];}
 function paint(){
  frame=0;if(!pending||pending.until&&Date.now()>pending.until)return;
  const view=viewer.getPageView(pending.page-1),page=view?.div;if(view?.renderingState!==3||!page?.querySelector('canvas'))return;
  if(!pending.until)pending.until=Date.now()+5000;
  marks.forEach(el=>el.remove());marks=[];
  for(const [x,y,w,h] of pending.rects){const el=document.createElement('div');el.className='pdf-citation-highlight';el.setAttribute('aria-hidden','true');Object.assign(el.style,{left:x/100+'%',top:y/100+'%',width:w/100+'%',height:h/100+'%'});page.append(el);marks.push(el);}
  if(pending.scroll){pending.scroll=false;marks[0]?.scrollIntoView({block:'center',inline:'nearest'});}
  clearTimeout(timer);timer=setTimeout(()=>{clear();pending=null;},Math.max(1,pending.until-Date.now()));
 }
 eventBus.on('pagerendered',({pageNumber})=>{if(pageNumber===pending?.page)paint();});
 eventBus.on('pagechanging',({pageNumber})=>{if(pending?.until&&pageNumber!==pending.page){clear();pending=null;}});
 return {show(anchor){clear();pending=null;notice.hidden=true;if(!anchor.rects)return;
  if(anchor.fingerprint!==fingerprint){notice.textContent='PDF 版本与引用不一致，已跳到引用页，请核对原文。';notice.hidden=false;return;}
  pending={...anchor,until:0,scroll:true};frame=requestAnimationFrame(paint);
 },clear(){clear();pending=null;}};
}

export function installPDFTools({source,pdfDocument,viewer,fingerprint,send}){
 const $=selector=>document.querySelector(selector),container=$('#pdf-container');
 const actions=document.createElement('div');actions.className='pdf-quote-tools';actions.innerHTML='<button type="button" id="pdf-return-notes" title="切回笔记 · Ctrl/⌘ Shift Enter" aria-label="切回笔记">'+window.WorkmoireIcons.render('write')+'</button><span id="pdf-quote-status">选择原文后可引用到笔记</span><button type="button" id="pdf-crop-toggle" aria-pressed="false">框选图表</button><button type="button" id="pdf-copy-quote" disabled>复制引用</button><button type="button" id="pdf-insert-quote" disabled>引用到笔记</button><button type="button" id="pdf-crop-cancel" hidden>取消</button><button type="button" id="pdf-crop-insert" hidden disabled>插入笔记</button>';document.body.append(actions);document.body.classList.add('pdf-desk');
 let selection=null,cropping=false,drag=null,chosen=null,box=null,captureTask=null,busy=false,generation=0,requestId=null;
 const setStatus=text=>$('#pdf-quote-status').textContent=text;
 function paint(){
  for(const id of ['pdf-copy-quote','pdf-insert-quote','pdf-crop-toggle'])$('#'+id).hidden=cropping;
  for(const id of ['pdf-crop-insert','pdf-crop-cancel'])$('#'+id).hidden=!cropping;
  $('#pdf-insert-quote').disabled=!selection;$('#pdf-copy-quote').disabled=!selection;$('#pdf-crop-insert').disabled=busy||!chosen;$('#pdf-crop-cancel').disabled=busy&&Boolean(requestId);
  $('#pdf-crop-toggle').setAttribute('aria-pressed',String(cropping));document.body.classList.toggle('pdf-cropping',cropping);
 }
 function removeBox(){box?.remove();box=null;}
 function cancel(){if(!cropping)return false;if(busy&&requestId)return true;generation++;captureTask?.cancel();captureTask=null;busy=false;cropping=false;chosen=null;drag=null;removeBox();paint();setStatus('选择原文后可引用到笔记');return true;}
 function readSelection(){
  if(cropping)return;selection=null;const selected=getSelection();
  if(selected?.rangeCount&&!selected.isCollapsed){const range=selected.getRangeAt(0),element=node=>node.nodeType===1?node:node.parentElement,start=element(range.startContainer),end=element(range.endContainer);
   if(start?.closest('.textLayer')&&end?.closest('.textLayer')){const pageNode=start.closest('.page'),page=Number(pageNode?.dataset.pageNumber),endPage=Number(end.closest('.page')?.dataset.pageNumber),text=selected.toString().trim();
    if(text&&text.length<=12000&&page>=1&&endPage>=page&&endPage<=viewer.pagesCount)selection={text,page,endPage,...textAnchor(range,pageNode,fingerprint)};
   }
  }
  paint();setStatus(selection?'已选择 '+selection.text.length+' 字 · 第 '+selection.page+' 页':'选择原文后可引用到笔记');
 }
 document.addEventListener('selectionchange',readSelection);
 for(const [id,action] of [['pdf-insert-quote','insert'],['pdf-copy-quote','copy']]){const button=$('#'+id);button.onmousedown=e=>e.preventDefault();button.onclick=()=>{if(selection)send({type:'workmoire:pdf-quote',action,...selection});};}
 $('#pdf-return-notes').onclick=()=>send({type:'workmoire:pdf-command',action:'notes'});
 $('#pdf-crop-toggle').onclick=()=>{getSelection()?.removeAllRanges();cropping=true;chosen=null;paint();setStatus('在一页内拖动框选图表或公式');};
 $('#pdf-crop-cancel').onclick=cancel;
 function point(event,page){const r=page.getBoundingClientRect();return {x:Math.max(r.left,Math.min(r.right,event.clientX)),y:Math.max(r.top,Math.min(r.bottom,event.clientY))};}
 container.addEventListener('pointerdown',event=>{
  if(!cropping||busy||event.button!==0)return;const page=event.target.closest('.page');if(!page)return;event.preventDefault();event.stopPropagation();removeBox();chosen=null;const start=point(event,page);drag={id:event.pointerId,page,start};container.setPointerCapture(event.pointerId);box=document.createElement('div');box.className='pdf-crop-box';page.append(box);paint();
 },true);
 container.addEventListener('pointermove',event=>{
  if(!drag)return;event.preventDefault();const end=point(event,drag.page),r={left:Math.min(drag.start.x,end.x),top:Math.min(drag.start.y,end.y),right:Math.max(drag.start.x,end.x),bottom:Math.max(drag.start.y,end.y)},rect=normalizedRectangle(r,drag.page.getBoundingClientRect());
  chosen=r.right-r.left>=6&&r.bottom-r.top>=6&&rect?{page:Number(drag.page.dataset.pageNumber),rects:[rect],fingerprint}:null;
  if(rect)Object.assign(box.style,{left:rect[0]/100+'%',top:rect[1]/100+'%',width:rect[2]/100+'%',height:rect[3]/100+'%'});
  paint();
 },true);
 function release(cancelled){if(!drag)return;const id=drag.id;drag=null;if(container.hasPointerCapture(id))container.releasePointerCapture(id);if(cancelled){chosen=null;removeBox();}paint();if(chosen)setStatus('第 '+chosen.page+' 页 · 确认后插入笔记');}
 container.addEventListener('pointerup',()=>release(false));container.addEventListener('pointercancel',()=>release(true));
 $('#pdf-crop-insert').onclick=async()=>{
  if(!chosen||busy)return;const capture={...chosen},version=++generation;busy=true;paint();setStatus('正在生成清晰截图…');
  try{
   const page=await pdfDocument.getPage(capture.page),unit=page.getViewport({scale:1}),r=capture.rects[0];
   const width=unit.width*r[2]/10000,height=unit.height*r[3]/10000,scale=Math.min(3,3072/Math.max(width,height),Math.sqrt(4_000_000/(width*height)));
   if(width<1||height<1)throw new Error('选区太小，请重新框选。');
   const viewport=page.getViewport({scale}),canvas=document.createElement('canvas');canvas.width=Math.max(1,Math.ceil(width*scale));canvas.height=Math.max(1,Math.ceil(height*scale));
   captureTask=page.render({canvasContext:canvas.getContext('2d'),viewport,transform:[1,0,0,1,-viewport.width*r[0]/10000,-viewport.height*r[1]/10000],background:'#ffffff'});await captureTask.promise;captureTask=null;
   const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/png'));canvas.width=canvas.height=0;
   if(version!==generation)return;if(!blob||blob.size>12*1024*1024)throw new Error('截图过大，请缩小选区。');
   requestId='crop-'+Date.now()+'-'+generation;setStatus('正在上传并插入…');paint();send({type:'workmoire:pdf-capture',requestId,blob,displayWidth:Math.round(width*4/3),...capture});
  }catch(error){if(version!==generation)return;busy=false;paint();setStatus(error.name==='RenderingCancelledException'?'已取消框选':error.message||'截图生成失败，请重试。');}
 };
 window.addEventListener('message',event=>{
  if(event.origin!==location.origin||event.source!==parent||event.data?.type!=='workmoire:pdf-capture-result'||event.data.requestId!==requestId||!requestId)return;
  requestId=null;busy=false;if(event.data.ok){cropping=false;chosen=null;removeBox();paint();setStatus('图表已插入笔记');}else{paint();setStatus('插入失败，请重试。');}
 });
 paint();return {cancel};
}
