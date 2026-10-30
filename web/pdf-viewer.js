import * as pdfjs from "pdfjs-dist/build/pdf.mjs";
import {pdfSource,parsePDFAnchor,pdfFragment} from './pdf-source.js';
import {citationHighlighter,installPDFTools} from './pdf-annotations.js';
// The upstream viewer consumes this shared instance; avoid duplicating the PDF API.
globalThis.pdfjsLib=pdfjs;
const {PDFViewer,EventBus,PDFLinkService,PDFFindController}=await import("pdfjs-dist/web/pdf_viewer.mjs");
pdfjs.GlobalWorkerOptions.workerSrc="/static/vendor/pdf.worker.min.mjs?v=20261027";
const $=selector=>document.querySelector(selector),status=$("#pdf-status");
try{
 const params=new URLSearchParams(location.search),source=pdfSource(params.get('file')||'');
 if(!source)throw new Error('Invalid PDF source');
 const eventBus=new EventBus(),container=$('#pdf-container');
 const linkService=new PDFLinkService({eventBus,externalLinkTarget:2,externalLinkRel:'noopener noreferrer'});
 const findController=new PDFFindController({eventBus,linkService});
 const viewer=new PDFViewer({container,viewer:$('#pdf-pages'),eventBus,linkService,findController,textLayerMode:1,annotationMode:1,enableAutoLinking:false,maxCanvasPixels:12000000,removePageBorders:true});
 linkService.setViewer(viewer);
 const key='workmoire:pdf-view:'+source.path.split('/').at(-1)+(params.get('desk')==='1'?':desk':':inline'),allowedZoom=new Set(['page-width','page-fit','1','1.25','1.5','2']);
 let fingerprint='',ready=false,restoring=true,saved=null,pending=null,storeTimer=0,highlighter=null,pdfTools=null,queuedTarget=null;
 if(source.privateFile)try{saved=JSON.parse(localStorage.getItem(key)||'null');}catch{}
 function persist(){
  clearTimeout(storeTimer);if(!source.privateFile||!ready||restoring)return;
  // Flush a just-selected page even when its deferred viewport event has not run.
  if(!pending||pending.page!==viewer.currentPageNumber)pending={fingerprint,page:viewer.currentPageNumber,zoom:$('#pdf-zoom').value,left:0,top:null};
  try{localStorage.setItem(key,JSON.stringify(pending));}catch{}
 }
 function navigate(target){
  const anchor=parsePDFAnchor(pdfFragment(target)),page=anchor?.page;
  if(!ready){queuedTarget=anchor;return Boolean(anchor);}
  if(!anchor||page>viewer.pagesCount){status.hidden=false;status.textContent='引用页码超出这份 PDF 的范围。';return false;}
  status.hidden=true;viewer.scrollPageIntoView({pageNumber:page});highlighter?.show(anchor);return true;
 }
 const hashPage=()=>parsePDFAnchor(location.hash);
 eventBus.on('pagesinit',()=>{
  ready=true;$('#pdf-total').textContent=viewer.pagesCount;$('#pdf-page').max=viewer.pagesCount;status.hidden=true;
  const previous=saved?.fingerprint===fingerprint?saved:null,zoom=allowedZoom.has(String(previous?.zoom))?String(previous.zoom):'page-width';
  $('#pdf-zoom').value=zoom;viewer.currentScaleValue=zoom;
  requestAnimationFrame(()=>{
   const explicit=queuedTarget||hashPage();queuedTarget=null;
   if(explicit)navigate(explicit);
   else if(previous&&Number.isInteger(previous.page)&&previous.page>=1&&previous.page<=viewer.pagesCount){
    viewer.scrollPageIntoView({pageNumber:previous.page,destArray:[null,{name:'XYZ'},Number.isFinite(previous.left)?previous.left:0,Number.isFinite(previous.top)?previous.top:null,null],allowNegativeOffset:true});
   }
   restoring=false;
  });
 });
 eventBus.on('pagechanging',({pageNumber})=>{$('#pdf-page').value=pageNumber;$('#pdf-prev').disabled=pageNumber<=1;$('#pdf-next').disabled=pageNumber>=viewer.pagesCount;});
 eventBus.on('pagerendered',()=>{document.body.dataset.ready='true';});
 eventBus.on('updateviewarea',({location:area})=>{
  if(!ready||restoring||!container.clientWidth||!container.clientHeight)return;
  pending={fingerprint,page:area.pageNumber,zoom:$('#pdf-zoom').value,left:area.left,top:area.top};
  clearTimeout(storeTimer);storeTimer=setTimeout(persist,180);
 });
 const desk=source.privateFile&&params.get('desk')==='1'&&parent!==window;
 const send=data=>parent.postMessage({...data,source:source.path},location.origin);
 container.tabIndex=0;
 document.addEventListener('keydown',event=>{
  if(event.isComposing||event.keyCode===229)return;const mod=event.ctrlKey||event.metaKey,key=event.key.toLowerCase();
  if(mod&&key==='f'){event.preventDefault();$('#pdf-search').hidden=false;$('#pdf-find').focus();return;}
  if(desk&&mod&&key==='s'){event.preventDefault();send({type:'workmoire:pdf-command',action:'save'});return;}
  if(desk&&mod&&event.shiftKey&&event.key==='Enter'){event.preventDefault();send({type:'workmoire:pdf-command',action:'notes'});return;}
  if(event.key==='Escape'){
   if(pdfTools?.cancel()){event.preventDefault();return;}
   if(!$('#pdf-search').hidden){event.preventDefault();$('#pdf-search').hidden=true;container.focus();return;}
   if(desk){event.preventDefault();send({type:'workmoire:pdf-command',action:'exit'});}
  }
 });
 const task=pdfjs.getDocument({url:source.src,withCredentials:true,isEvalSupported:false,cMapUrl:'/static/vendor/pdf-cmaps/',cMapPacked:true,standardFontDataUrl:'/static/vendor/pdf-fonts/',wasmUrl:'/static/vendor/pdf-wasm/',useWorkerFetch:true});
 const pdfDocument=await task.promise;fingerprint=pdfDocument.fingerprints[0];
 const notice=document.createElement('p');notice.id='pdf-citation-notice';notice.hidden=true;notice.setAttribute('role','status');document.body.append(notice);
 highlighter=citationHighlighter({viewer,eventBus,fingerprint,notice});
 window.WorkmoirePDF={source:source.path,navigate,save:persist,snapshot:()=>({page:viewer.currentPageNumber,zoom:$('#pdf-zoom').value,fingerprint})};
 viewer.setDocument(pdfDocument);linkService.setDocument(pdfDocument);
 $('#pdf-prev').onclick=()=>{if(viewer.currentPageNumber>1)navigate(viewer.currentPageNumber-1);};
 $('#pdf-next').onclick=()=>{if(viewer.currentPageNumber<viewer.pagesCount)navigate(viewer.currentPageNumber+1);};
 $('#pdf-page').onchange=event=>navigate(Number(event.target.value));
 $('#pdf-zoom').onchange=event=>{viewer.currentScaleValue=event.target.value;};
 $('#pdf-open').href=source.src;$('#pdf-download').href=source.path;
 let findTimer;
 const find=(type='',previous=false)=>eventBus.dispatch('find',{source:window,type,query:$('#pdf-find').value,phraseSearch:true,caseSensitive:false,entireWord:false,highlightAll:true,findPrevious:previous,matchDiacritics:false});
 $('#pdf-find').oninput=()=>{clearTimeout(findTimer);findTimer=setTimeout(()=>find(),180);};
 $('#pdf-find').onkeydown=event=>{if(event.key==='Enter'){event.preventDefault();find('again',event.shiftKey);}};
 $('#pdf-find-button').onclick=()=>{$('#pdf-search').hidden=!$('#pdf-search').hidden;if(!$('#pdf-search').hidden)$('#pdf-find').focus();};
 const observer=new ResizeObserver(()=>{if(container.clientWidth&&container.clientHeight&&['page-width','page-fit'].includes($('#pdf-zoom').value))viewer.currentScaleValue=$('#pdf-zoom').value;});observer.observe(container);
 window.addEventListener('hashchange',()=>{const page=hashPage();if(page)navigate(page);});
 window.addEventListener('pagehide',persist);
 document.addEventListener('visibilitychange',()=>{if(document.hidden)persist();});
 if(desk)pdfTools=installPDFTools({source,pdfDocument,viewer,fingerprint,send});

}catch(error){document.body.dataset.error='true';status.hidden=false;status.textContent='PDF 暂时无法读取。请确认附件仍然存在且有访问权限，或在新窗口打开原文。';console.info('PDF preview unavailable:',error.name);}
