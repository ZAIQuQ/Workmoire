// Shared URL rules for private attachments and already-authorized share copies.
export function pdfSource(value,{shared=true}={}){
 try{
  const url=new URL(value,location.origin);
  if(url.origin!==location.origin||url.username||url.password)return null;
  const privateFile=/^\/files\/[a-f0-9]{32}$/.test(url.pathname);
  if(!privateFile&&!(shared&&/^\/s\/[A-Za-z0-9_-]{43}\/files\/[a-f0-9]{32}$/.test(url.pathname)))return null;
  return {path:url.pathname,src:url.pathname+'?inline=1',privateFile};
 }catch{return null;}
}
export function pdfCitation(value){
 const source=pdfSource(value);if(!source)return null;
 const hash=new URL(value,location.origin).hash,match=/^#page=([1-9][0-9]{0,4})$/.exec(hash);
 return match&&Number(match[1])<=10000?{...source,page:Number(match[1])}:null;
}
export function pdfViewerURL(source,page=null,desk=false){
 return '/static/pdf-viewer.html?v=20261029-reading-desk&file='+encodeURIComponent(source.src)+(desk?'&desk=1':'')+(page?'#page='+page:'');
}
