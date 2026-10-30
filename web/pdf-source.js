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
 const anchor=parsePDFAnchor(new URL(value,location.origin).hash);
 return anchor?{...source,...anchor}:null;
}
export function parsePDFAnchor(hash){
 if(String(hash||'').replace(/^#/,'').length>1200)return null;
 const match=/^#?page=([1-9][0-9]{0,4})(?:&rect=([0-9,;]+)&fp=([a-f0-9]{32,64}))?$/.exec(String(hash||''));
 if(!match||Number(match[1])>10000)return null;
 const result={page:Number(match[1])};if(!match[2])return result;
 const raw=match[2].split(';').map(rect=>rect.split(','));if(raw.some(r=>r.some(n=>!/^\d{1,5}$/.test(n))))return null;
 const rects=raw.map(rect=>rect.map(Number));
 if(rects.length>32||rects.some(r=>r.length!==4||r.some(n=>!Number.isInteger(n)||n<0||n>10000)||r[2]<1||r[3]<1||r[0]+r[2]>10000||r[1]+r[3]>10000))return null;
 return {...result,rects,fingerprint:match[3]};
}
export function pdfFragment(value){
 const anchor=typeof value==='number'?{page:value}:value;
 if(!anchor||!Number.isInteger(anchor.page)||anchor.rects!==undefined&&(!Array.isArray(anchor.rects)||anchor.rects.some(r=>!Array.isArray(r)||r.length!==4||r.some(n=>!Number.isInteger(n)))))return '';
 const fragment='page='+anchor?.page+(anchor?.rects?.length?'&rect='+anchor.rects.map(r=>r.join(',')).join(';')+'&fp='+anchor.fingerprint:'');
 return parsePDFAnchor(fragment)?'#'+fragment:'';
}
export function pdfViewerURL(source,target=null,desk=false){
 return '/static/pdf-viewer.html?v=20261030-reading-tools&file='+encodeURIComponent(source.src)+(desk?'&desk=1':'')+(target?pdfFragment(target):'');
}
