import * as pdfjs from "pdfjs-dist/build/pdf.mjs";
// The upstream viewer consumes this shared instance; avoid duplicating the PDF API.
globalThis.pdfjsLib=pdfjs;
const {PDFViewer,EventBus,PDFLinkService,PDFFindController}=await import("pdfjs-dist/web/pdf_viewer.mjs");
pdfjs.GlobalWorkerOptions.workerSrc="/static/vendor/pdf.worker.min.mjs?v=20261027";
const $=selector=>document.querySelector(selector);
const status=$("#pdf-status");
try{
  const parameter=new URLSearchParams(location.search).get("file")||"";
  const source=new URL(parameter,location.origin);
  if(source.origin!==location.origin||!(/^\/files\/[a-f0-9]{32}$/.test(source.pathname)||/^\/s\/[A-Za-z0-9_-]{43}\/files\/[a-f0-9]{32}$/.test(source.pathname)))throw new Error("PDF 地址无效，请重新插入附件");
  source.search="?inline=1";
  const eventBus=new EventBus();
  const linkService=new PDFLinkService({eventBus,externalLinkTarget:2,externalLinkRel:"noopener noreferrer"});
  const findController=new PDFFindController({eventBus,linkService});
  const viewer=new PDFViewer({container:$("#pdf-container"),viewer:$("#pdf-pages"),eventBus,linkService,findController,textLayerMode:1,annotationMode:1,enableAutoLinking:false,maxCanvasPixels:12000000,removePageBorders:true});
  linkService.setViewer(viewer);
  eventBus.on("pagesinit",()=>{viewer.currentScaleValue="page-width";$("#pdf-total").textContent=viewer.pagesCount;status.hidden=true;});
  eventBus.on("pagechanging",({pageNumber})=>{$("#pdf-page").value=pageNumber;});
  eventBus.on("pagerendered",()=>{document.body.dataset.ready="true";});
  const pdfDocument=await pdfjs.getDocument({url:source.href,withCredentials:true,isEvalSupported:false,cMapUrl:"/static/vendor/pdf-cmaps/",cMapPacked:true,standardFontDataUrl:"/static/vendor/pdf-fonts/",wasmUrl:"/static/vendor/pdf-wasm/",useWorkerFetch:true}).promise;
  viewer.setDocument(pdfDocument);linkService.setDocument(pdfDocument);
  $("#pdf-prev").onclick=()=>{if(viewer.currentPageNumber>1)viewer.currentPageNumber--;};
  $("#pdf-next").onclick=()=>{if(viewer.currentPageNumber<viewer.pagesCount)viewer.currentPageNumber++;};
  $("#pdf-page").onchange=event=>{viewer.currentPageNumber=Math.max(1,Math.min(viewer.pagesCount,Number(event.target.value)||1));};
  $("#pdf-zoom").onchange=event=>{viewer.currentScaleValue=event.target.value;};
  $("#pdf-open").href=source.href;$("#pdf-download").href=source.pathname;
  let timer;
  const find=(type="",previous=false)=>eventBus.dispatch("find",{source:window,type,query:$("#pdf-find").value,phraseSearch:true,caseSensitive:false,entireWord:false,highlightAll:true,findPrevious:previous,matchDiacritics:false});
  $("#pdf-find").oninput=()=>{clearTimeout(timer);timer=setTimeout(()=>find(),180);};
  $("#pdf-find").onkeydown=event=>{if(event.key==="Enter"){event.preventDefault();find("again",event.shiftKey);}};
  $("#pdf-find-button").onclick=()=>{$("#pdf-search").hidden=!$("#pdf-search").hidden;if(!$("#pdf-search").hidden)$("#pdf-find").focus();};
  const observer=new ResizeObserver(()=>{if($("#pdf-zoom").value==="page-width")viewer.currentScaleValue="page-width";});observer.observe($("#pdf-container"));
}catch(error){status.hidden=false;status.textContent="PDF 暂时无法读取。请确认已登录，或在新窗口打开原文。";console.info("PDF preview unavailable:",error.name);}
