import {getDocument,GlobalWorkerOptions} from 'pdfjs-dist/build/pdf.mjs';
GlobalWorkerOptions.workerSrc='/static/vendor/pdf.worker.min.mjs?v=20261027';
export async function extractPaperPDF(source,{onProgress=()=>{}}={}){
 let location;
 if(source instanceof Blob){onProgress({stage:'opening'});location={data:new Uint8Array(await source.arrayBuffer())};}
 else{if(!/^[a-f0-9]{32}$/.test(source))throw new Error('PDF 附件地址无效');location={url:'/files/'+source+'?inline=1',withCredentials:true};}
 const task=getDocument({...location,isEvalSupported:false,disableFontFace:true,cMapUrl:'/static/vendor/pdf-cmaps/',cMapPacked:true,standardFontDataUrl:'/static/vendor/pdf-fonts/',wasmUrl:'/static/vendor/pdf-wasm/',useWorkerFetch:true});
 task.onProgress=event=>onProgress({stage:'loading',loaded:event.loaded,total:event.total});
 let expired=false;const timeout=setTimeout(()=>{expired=true;task.destroy().catch(()=>{});},45000);
 try{
  const doc=await task.promise,meta=await doc.getMetadata().catch(()=>({info:{}}));let text='',pagesRead=0,truncated=false;const total=Math.min(doc.numPages,80);onProgress({stage:'extracting',done:0,total});
  for(let number=1;number<=total;number++){
   const page=await doc.getPage(number),reader=page.streamTextContent().getReader();text+='\n[第 '+number+' 页]\n';pagesRead=number;
   try{while(true){const {value,done}=await reader.read();if(done)break;for(const item of value.items){if(typeof item.str!=='string')continue;const part=item.str+(item.hasEOL?'\n':' ');const room=60000-text.length;if(part.length>room)truncated=true;text+=part.slice(0,Math.max(0,room));if(text.length>=60000)break;}if(text.length>=60000){truncated=true;await reader.cancel();break;}}}finally{page.cleanup();}
   onProgress({stage:'extracting',done:number,total});if(text.length>=60000)break;
  }
  truncated ||= pagesRead<doc.numPages;
  return {text:text.trim(),pages_read:pagesRead,page_count:doc.numPages,truncated,title:String(meta.info?.Title||'').slice(0,200),author:String(meta.info?.Author||'').slice(0,200)};
 }catch(error){throw new Error(expired?'PDF 文字读取超时，可尝试较小的文件':error.name==='PasswordException'?'PDF 已加密，请先上传可直接阅读的版本':'无法解析这个 PDF，请更换有效的 PDF 文件');}
 finally{clearTimeout(timeout);await task.destroy();}
}
