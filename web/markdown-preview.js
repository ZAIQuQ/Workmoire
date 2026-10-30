import MarkdownIt from "markdown-it";
import katex from "katex";
import hljs from "highlight.js/lib/core";
import javascript from "highlight.js/lib/languages/javascript";
import python from "highlight.js/lib/languages/python";
import cpp from "highlight.js/lib/languages/cpp";
import json from "highlight.js/lib/languages/json";
import sqlHighlight from "highlight.js/lib/languages/sql";
import bash from "highlight.js/lib/languages/bash";
import xml from "highlight.js/lib/languages/xml";
import css from "highlight.js/lib/languages/css";
import latex from "highlight.js/lib/languages/latex";

for (const [name,language] of Object.entries({javascript,python,cpp,json,sql:sqlHighlight,bash,xml,css,latex})) hljs.registerLanguage(name,language);
const uiIcon = name => window.WorkmoireIcons.render(name);
const escape = value => String(value).replace(/[&<>"']/g, ch=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
export function safeMedia(value) {
  try {
    const url = new URL(value, location.origin);
    if (url.origin === location.origin) return (/^\/files\/[a-f0-9]{32}$/.test(url.pathname)||/^\/s\/[A-Za-z0-9_-]{43}\/files\/[a-f0-9]{32}$/.test(url.pathname)) ? url.pathname+url.search : null;
    return url.protocol === "https:" && !url.username && !url.password ? url.href : null;
  } catch { return null; }
}
const md = new MarkdownIt({html:false,linkify:true,breaks:true,typographer:true,highlight(code,lang){
  const content=lang&&hljs.getLanguage(lang)?hljs.highlight(code,{language:lang,ignoreIllegals:true}).value:escape(code);
  return '<pre class="code-block"><div class="code-head"><span>'+escape(lang||"text")+'</span><button type="button" class="copy-code">复制</button></div><code class="hljs">'+content+'</code></pre>';
}});
export function mathHTML(source,displayMode){
  try{return katex.renderToString(source,{displayMode,throwOnError:false,trust:false,strict:false,maxExpand:500,maxSize:20,output:"htmlAndMathml"});}
  catch{return '<code class="math-error">'+escape(source)+'</code>';}
}
md.inline.ruler.before("escape","research_math",(state,silent)=>{
  const start=state.pos,src=state.src;
  let open,close;
  if(src.startsWith("\\(",start)){open="\\(";close="\\)";}
  else if(src[start]==="$"&&src[start+1]!=="$"&&!/\s/.test(src[start+1]||" ")){open="$";close="$";}
  else return false;
  let end=src.indexOf(close,start+open.length);
  while(end>=0&&src[end-1]==="\\")end=src.indexOf(close,end+close.length);
  if(end<0||src.slice(start+open.length,end).includes("\n\n"))return false;
  if(close==="$"&&(/\s/.test(src[end-1]||" ")||/\d/.test(src[end+1]||"")))return false;
  if(!silent){const token=state.push("math_inline","",0);token.content=src.slice(start+open.length,end);}
  state.pos=end+close.length;return true;
});
md.renderer.rules.math_inline=(tokens,index)=>mathHTML(tokens[index].content,false);
md.block.ruler.before("fence","research_math_block",(state,startLine,endLine,silent)=>{
  const start=state.bMarks[startLine]+state.tShift[startLine];
  const first=state.src.slice(start,state.eMarks[startLine]).trim();
  const open=first.startsWith("$$")?"$$":first.startsWith("\\[")?"\\[":null;
  if(!open)return false;
  const close=open==="$$"?"$$":"\\]";
  let body=first.slice(open.length),next=startLine;
  const same=body.indexOf(close);
  if(same>=0)body=body.slice(0,same);
  else{
    let found=false;
    while(++next<endLine){
      const line=state.src.slice(state.bMarks[next]+state.tShift[next],state.eMarks[next]);
      const end=line.indexOf(close);
      body+="\n"+(end>=0?line.slice(0,end):line);
      if(end>=0){found=true;break;}
    }
    if(!found)return false;
  }
  if(silent)return true;
  const token=state.push("math_block","",0);token.block=true;token.content=body.trim();token.map=[startLine,next+1];
  state.line=next+1;return true;
});
md.renderer.rules.math_block=(tokens,index)=>'<div class="math-block">'+mathHTML(tokens[index].content,true)+'</div>';
md.block.ruler.before("paragraph","research_pdf",(state,startLine,endLine,silent)=>{
  const line=state.src.slice(state.bMarks[startLine]+state.tShift[startLine],state.eMarks[startLine]);
  const match=/^@\[pdf\]\((.+)\)\s*$/i.exec(line);
  if(!match)return false;
  if(silent)return true;
  const token=state.push("pdf_embed","",0);token.block=true;token.content=match[1];token.map=[startLine,startLine+1];state.line=startLine+1;return true;
});
md.renderer.rules.pdf_embed=(tokens,index)=>{
  const url=safeMedia(tokens[index].content);
  if(!url)return '<p class="media-error">PDF 链接无效，请使用上传的附件或 HTTPS 链接。</p>';
  if(new URL(url,location.origin).origin!==location.origin)return '<figure class="pdf-embed external-pdf"><figcaption><span>PDF · 原文资料</span><a href="'+escape(url)+'" target="_blank" rel="noopener noreferrer">打开原文 '+uiIcon("arrow")+'</a></figcaption><div class="external-pdf-body"><span>请下载原文后，通过「插入 PDF」上传本地文件。</span></div></figure>';
  return '<figure class="pdf-embed"><figcaption><span>PDF · 原文阅读</span><a href="'+escape(url)+'" target="_blank" rel="noopener noreferrer">新窗口打开 '+uiIcon("arrow")+'</a></figcaption><iframe src="/static/pdf-viewer.html?v=20261030-reading-tools&amp;file='+encodeURIComponent(url)+'" title="内嵌 PDF 阅读器" loading="lazy" referrerpolicy="no-referrer"></iframe><div class="pdf-fallback">无法显示？可以在新窗口打开阅读。</div></figure>';
};
md.inline.ruler.before("link","document_reference",(state,silent)=>{
  const match=/^\[\[(\d+)\|([^\]\n]+)\]\]/.exec(state.src.slice(state.pos));
  if(!match)return false;
  if(!silent){const token=state.push("document_reference","",0);token.content=match[2];token.meta={id:match[1]};}
  state.pos+=match[0].length;return true;
});
md.renderer.rules.document_reference=(tokens,index)=>'<button type="button" class="document-ref" data-document-id="'+tokens[index].meta.id+'">'+uiIcon("arrow")+escape(tokens[index].content)+'</button>';
md.core.ruler.after("inline","research_tasks",state=>{
  const stack=[];
  for(let i=0;i<state.tokens.length;i++){
    const token=state.tokens[i];
    if(token.type==="list_item_open")stack.push(token.map?.[0]);
    if(token.type==="list_item_close")stack.pop();
    if(token.type!=="inline"||!stack.length)continue;
    const first=token.children?.[0];
    const match=first?.type==="text"&&/^\[([ xX])\] /.exec(first.content);
    if(!match)continue;
    first.content=first.content.slice(4);
    const checkbox=new state.Token("html_inline","",0);
    checkbox.content='<input class="task-check" type="checkbox" aria-label="切换待办状态" data-task-line="'+stack.at(-1)+'" '+(match[1].toLowerCase()==="x"?"checked":"")+'>';
    token.children.unshift(checkbox);
  }
});
const originalImage=md.renderer.rules.image;
md.renderer.rules.image=(tokens,index,options,env,self)=>{
  const token=tokens[index],url=safeMedia(token.attrGet("src"));
  if(!url)return '<span class="media-error">图片链接无效</span>';
  token.attrSet("src",url);token.attrSet("loading","lazy");token.attrSet("referrerpolicy","no-referrer");
  return originalImage(tokens,index,options,env,self);
};
md.renderer.rules.heading_open=(tokens,index)=>'<'+tokens[index].tag+' id="document-heading-'+(tokens.slice(0,index).filter(t=>t.type==="heading_open").length)+'">';

export const renderPreview = source => md.render(String(source || ""));
