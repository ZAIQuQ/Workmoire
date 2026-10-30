import {Node, Extension, mergeAttributes, InputRule} from '@tiptap/core';
import Image from '@tiptap/extension-image';
import Link from '@tiptap/extension-link';
import {Marked, Lexer} from 'marked';
import {safeMedia, mathHTML, renderPreview} from './markdown-preview.js';

const icon = name => window.WorkmoireIcons.render(name);
export function safeLink(value) {
  if(typeof value!=='string'||!value.trim()||/[\x00-\x20\x7f]/.test(value)||value.length>3000)return null;
  if(/^#[\w-]+$/.test(value))return value;
  try {
    const url=new URL(value,location.origin);
    if(url.username||url.password)return null;
    if(url.origin===location.origin&&/^\/files\/[a-f0-9]{32}$/.test(url.pathname))return url.pathname+url.search+url.hash;
    return ['http:','https:','mailto:'].includes(url.protocol)?url.href:null;
  } catch {return null;}
}

// Raw HTML in imported Markdown remains literal text. Native HTML clipboard
// content is separately parsed through ProseMirror's registered node schema.
function literalHTML(tokens,block) {
  for(const token of tokens){
    if(token.type==='html'){
      const text=token.raw||token.text||'';
      Object.assign(token,block?{type:'paragraph',text,tokens:[{type:'text',raw:text,text}]}:{type:'text',text});
    }
  }
  return tokens;
}
class LiteralHTMLLexer extends Lexer {
  blockTokens(...args){return literalHTML(super.blockTokens(...args),true);}
  inlineTokens(...args){return literalHTML(super.inlineTokens(...args),false);}
}
export function safeMarkdownParser(){const instance=new Marked();instance.Lexer=LiteralHTMLLexer;return instance;}

function markdownLabel(value){return String(value||'').replace(/\\/g,'\\\\').replace(/\[/g,'\\[').replace(/\]/g,'\\]').replace(/[\r\n]/g,' ');}
function markdownURL(value){return String(value||'').replace(/\(/g,'%28').replace(/\)/g,'%29');}
function markdownTitle(value){return String(value||'').replace(/\\/g,'\\\\').replace(/"/g,'\\"').replace(/[\r\n]/g,' ');}

export const SafeLink=Link.extend({
  addAttributes(){return {...this.parent?.(),target:{default:'_blank',parseHTML:()=>'_blank'},rel:{default:'noopener noreferrer nofollow',parseHTML:()=> 'noopener noreferrer nofollow'},class:{default:null,parseHTML:()=>null}};},
  renderMarkdown(node,helpers){const title=node.attrs?.title;return '['+helpers.renderChildren(node)+']('+markdownURL(node.attrs?.href)+(title?' "'+markdownTitle(title)+'"':'')+')';},
  parseMarkdown(token,helpers){const href=safeLink(token.href);const content=helpers.parseInline(token.tokens||[]);return href?helpers.applyMark('link',content,{href,title:token.title||null,target:'_blank',rel:'noopener noreferrer nofollow'}):content;},
}).configure({openOnClick:false,autolink:true,linkOnPaste:true,defaultProtocol:'https',isAllowedUri:value=>Boolean(safeLink(value)),HTMLAttributes:{target:'_blank',rel:'noopener noreferrer nofollow'}});

export const SafeImage=Image.extend({
  addAttributes(){
    return {...this.parent?.(),
      src:{default:null,parseHTML:element=>safeMedia(element.getAttribute('src')),renderHTML:attrs=>({src:safeMedia(attrs.src)||''})},
      width:{default:null,parseHTML:element=>dimension(element.getAttribute('width'))},
      height:{default:null,parseHTML:element=>dimension(element.getAttribute('height'))},
    };
  },
  parseHTML(){return [{tag:'img[src]',getAttrs:element=>safeMedia(element.getAttribute('src'))?{}:false}];},
  renderMarkdown(node){const title=node.attrs?.title;return '!['+markdownLabel(node.attrs?.alt)+']('+markdownURL(node.attrs?.src)+(title?' "'+markdownTitle(title)+'"':'')+')';},
  parseMarkdown(token,helpers){
    const src=safeMedia(token.href);
    return src?helpers.createNode('image',{src,alt:token.text||'',title:token.title||null}):helpers.createTextNode(token.raw||token.text||'图片链接无效');
  },
}).configure({allowBase64:false,resize:{enabled:true,directions:['bottom-left','bottom-right'],minWidth:80,minHeight:40,alwaysPreserveAspectRatio:true},HTMLAttributes:{loading:'lazy',referrerpolicy:'no-referrer'}});
function dimension(value){const n=Number(value);return Number.isFinite(n)&&n>=16&&n<=8000?n:null;}

function mathExtension(name,inline,callbacks){
  return Node.create({
    name,group:inline?'inline':'block',inline,atom:true,draggable:!inline,selectable:true,
    addAttributes(){return {latex:{default:'',parseHTML:el=>el.getAttribute('data-latex')||el.querySelector('annotation[encoding="application/x-tex"]')?.textContent||''}};},
    parseHTML(){return [{tag:(inline?'span':'div')+'[data-type="'+name+'"]'}];},
    renderHTML({HTMLAttributes}){return [inline?'span':'div',mergeAttributes(HTMLAttributes,{'data-type':name,'data-latex':HTMLAttributes.latex,class:inline?'native-inline-math':'native-block-math'}),HTMLAttributes.latex||''];},
    markdownTokenName:name,
    markdownTokenizer:{
      name,level:inline?'inline':'block',
      start(source){if(!inline)return source.search(/^(?:\$\$|\\\[)/m);const indices=[source.indexOf('$'),source.indexOf('\\(')];const index=Math.min(...indices.filter(i=>i>=0),Infinity);return Number.isFinite(index)?index:-1;},
      tokenize(source){
        const match=inline?/^(?:\$(?!\$)([^\s$](?:[^$\n]*?[^\s$])?)\$(?!\d)|\\\(([\s\S]+?)\\\))/.exec(source):/^(?:\$\$\s*\n?([\s\S]*?)\$\$|\\\[\s*\n?([\s\S]*?)\\\])(?:\n|$)/.exec(source);
        if(match)return {type:name,raw:match[0],latex:(match[1]||match[2]||'').trim()};
      },
    },
    parseMarkdown(token){return {type:name,attrs:{latex:token.latex}};},
    renderMarkdown(node){const latex=node.attrs?.latex||'';return inline?'$'+latex+'$':'$$\n'+latex+'\n$$';},
    addInputRules(){return inline?[new InputRule({find:/\$([^$\n]+)\$$/,handler:({state,range,match})=>{state.tr.replaceWith(range.from,range.to,this.type.create({latex:match[1]}));}})]:[];},
    addNodeView(){return ({node,getPos,editor})=>{
      const dom=document.createElement(inline?'span':'div');dom.className=inline?'native-inline-math':'native-block-math';dom.contentEditable='false';dom.dataset.type=name;dom.tabIndex=0;dom.setAttribute('role','button');dom.setAttribute('aria-label','编辑公式');
      const paint=()=>{dom.dataset.latex=node.attrs.latex;dom.innerHTML=mathHTML(node.attrs.latex,!inline);dom.title=editor.isEditable?'点击编辑公式':node.attrs.latex;};paint();
      const edit=event=>{if(!editor.isEditable)return;event.preventDefault();event.stopPropagation();callbacks.math?.({inline,node,getPos});};dom.addEventListener('click',edit);dom.addEventListener('keydown',event=>{if(event.key==='Enter')edit(event);});
      return {dom,update(next){if(next.type!==node.type)return false;if(next.attrs.latex!==node.attrs.latex){node=next;paint();}return true;},stopEvent:event=>event.type!=='dragstart',ignoreMutation:()=>true};
    };},
  });
}

function latexBlockExtension(callbacks={}){
 return Node.create({
  name:'latexBlock',group:'block',atom:true,isolating:true,selectable:true,draggable:true,
  addAttributes(){return {source:{default:'',parseHTML:el=>el.getAttribute('data-source')||''}};},
  parseHTML(){return [{tag:'div[data-type="latexBlock"]'}];},
  renderHTML({node}){return ['div',{'data-type':'latexBlock','data-source':node.attrs.source||'',class:'latex-block'}];},
  markdownTokenName:'latexBlock',
  markdownTokenizer:{name:'latexBlock',level:'block',start:source=>source.search(/^:::latex[ \t]*$/m),tokenize(source){
   const match=/^:::latex[ \t]*\n([\s\S]*?)\n:::[ \t]*(?:\n|$)/.exec(source);
   if(match)return {type:'latexBlock',raw:match[0],source:match[1]};
  }},
  parseMarkdown:token=>({type:'latexBlock',attrs:{source:String(token.source||'')}}),
  renderMarkdown:node=>':::latex\n'+String(node.attrs?.source||'')+'\n:::',
  addNodeView(){return ({node,getPos,editor})=>{
   const dom=document.createElement('div');dom.className='latex-block';dom.contentEditable='false';dom.dataset.type='latexBlock';
   const head=document.createElement('div');head.className='latex-block-head';const tabs=document.createElement('div');tabs.className='latex-block-tabs';
   const write=document.createElement('button'),previewTab=document.createElement('button');for(const [button,label] of [[write,'Write'],[previewTab,'Preview']]){button.type='button';button.textContent=label;button.setAttribute('role','tab');button.setAttribute('aria-label',label+' LaTeX');tabs.append(button);}
   const count=document.createElement('span');count.className='latex-char-count';const copy=document.createElement('button');copy.type='button';copy.className='latex-copy';copy.textContent='复制 LaTeX';copy.setAttribute('aria-label','复制 LaTeX 源码');const body=document.createElement('div');body.className='latex-block-body';
   const textarea=document.createElement('textarea');textarea.className='latex-source';textarea.spellcheck=false;textarea.wrap='off';textarea.setAttribute('aria-label','LaTeX 源码');
   const rendered=document.createElement('div');rendered.className='latex-preview';rendered.setAttribute('aria-label','LaTeX 预览');rendered.setAttribute('role','img');
   body.append(textarea,rendered);const footer=document.createElement('div');footer.className='latex-block-footer';footer.innerHTML='<span class="latex-tex-mark" aria-hidden="true">TeX</span><span>TeX is supported</span>';head.append(tabs,count,copy);dom.append(head,body,footer);
   let nodeSource=node.attrs.source||'',mode=editor.isEditable?'write':'preview';
   const setNodeSource=value=>{const pos=getPos?.();if(typeof pos!=='number'||!editor.isEditable)return;editor.view.dispatch(editor.state.tr.setNodeMarkup(pos,undefined,{...node.attrs,source:value}));};
   const paint=()=>{if(textarea.value!==nodeSource)textarea.value=nodeSource;textarea.readOnly=!editor.isEditable;count.textContent=nodeSource.length+' 字符';const markdownLike=/```[\s\S]*```|(^|\n)\s*\*\*[^\n]+\*\*|(^|\n)\s*#{1,6}\s|(^|\n)\s*[-*+]\s|(^|\n)\s*\|[^\n]+\|\s*\n\s*\|?\s*:?-+:?\s*(?:\|\s*:?-+:?\s*)+\|?\s*(?:\n|$)|(?<!\\)\$[^$\n]+\$(?!\$)/m.test(nodeSource);rendered.innerHTML=markdownLike?renderPreview(nodeSource):mathHTML(nodeSource,true);rendered.dataset.previewKind=markdownLike?'markdown':'latex';textarea.hidden=mode!=='write';rendered.hidden=mode!=='preview';write.setAttribute('aria-selected',String(mode==='write'));previewTab.setAttribute('aria-selected',String(mode==='preview'));copy.hidden=editor.isEditable;dom.dataset.mode=mode;};
   const setMode=value=>{mode=value;paint();if(mode==='write'&&editor.isEditable)textarea.focus();};
   copy.onclick=async event=>{event.preventDefault();event.stopPropagation();try{await callbacks.copy?.(nodeSource);copy.textContent='已复制';setTimeout(()=>{if(copy.isConnected)copy.textContent='复制 LaTeX';},1200);}catch{copy.textContent='复制失败';}};
   write.onclick=event=>{event.preventDefault();event.stopPropagation();setMode('write');};previewTab.onclick=event=>{event.preventDefault();event.stopPropagation();setMode('preview');requestAnimationFrame(paint);};previewTab.onpointerup=event=>{event.preventDefault();event.stopPropagation();setMode('preview');};head.addEventListener('click',event=>{const button=event.target.closest('button');if(button===write||button===previewTab){event.preventDefault();event.stopPropagation();setMode(button===write?'write':'preview');requestAnimationFrame(paint);}},true);textarea.oninput=()=>{nodeSource=textarea.value;setNodeSource(nodeSource);paint();};textarea.onkeydown=event=>{if(event.key==='Tab'){if(!editor.isEditable)return;event.preventDefault();const start=textarea.selectionStart;textarea.setRangeText('  ',start,textarea.selectionEnd,'end');nodeSource=textarea.value;setNodeSource(nodeSource);paint();}};
   head.onmousedown=event=>{if(event.target.closest('button'))event.preventDefault();};paint();
   return {dom,update(next){if(next.type!==node.type)return false;node=next;nodeSource=next.attrs.source||'';if(!editor.isEditable)mode='preview';paint();return true;},stopEvent:event=>head.contains(event.target)||textarea.contains(event.target),ignoreMutation:()=>true};
  };
 },
 });
}

function pdfExtension(callbacks){
  return Node.create({
    name:'pdf',group:'block',atom:true,draggable:true,isolating:true,selectable:true,
    addAttributes(){return {src:{default:'',parseHTML:el=>safeMedia(el.getAttribute('data-src'))||''},title:{default:'PDF 原文'}};},
    parseHTML(){return [{tag:'figure[data-type="pdf"]',getAttrs:el=>safeMedia(el.getAttribute('data-src'))?{}:false}];},
    renderHTML({node}){return ['figure',{'data-type':'pdf','data-src':safeMedia(node.attrs.src)||'',class:'native-pdf'},['a',{href:safeMedia(node.attrs.src)||'',target:'_blank',rel:'noopener noreferrer'},node.attrs.title||'PDF 原文']];},
    markdownTokenName:'pdf',
    markdownTokenizer:{name:'pdf',level:'block',start:source=>source.search(/^@\[pdf\]\(/m),tokenize(source){const match=/^@\[pdf\]\(([^\n]+)\)[ \t]*(?:\n|$)/i.exec(source);if(match)return {type:'pdf',raw:match[0],src:match[1]};}},
    parseMarkdown(token){const src=safeMedia(token.src);return src?{type:'pdf',attrs:{src,title:'PDF 原文'}}:{type:'paragraph',content:[{type:'text',text:'PDF 链接无效'}]};},
    renderMarkdown:node=>'@[pdf]('+(node.attrs?.src||'')+')',
    addNodeView(){return ({node,getPos,editor})=>{
      const dom=document.createElement('figure');dom.className='native-pdf';dom.contentEditable='false';dom.dataset.type='pdf';
      const caption=document.createElement('figcaption'),label=document.createElement('span'),actions=document.createElement('span');actions.className='native-pdf-actions';
      const open=document.createElement('a');open.target='_blank';open.rel='noopener noreferrer';open.innerHTML='打开原文 '+icon('arrow');
      const remove=document.createElement('button');remove.type='button';remove.className='native-node-delete';remove.setAttribute('aria-label','移除 PDF 块');remove.title='移除 PDF 块';remove.innerHTML=icon('close');remove.onclick=()=>{const pos=getPos();if(editor.isEditable&&typeof pos==='number')editor.chain().focus().deleteRange({from:pos,to:pos+node.nodeSize}).run();};
      actions.append(open,remove);caption.append(label,actions);dom.append(caption);
      let body,source='';
      const paint=()=>{
        const src=safeMedia(node.attrs.src);label.textContent=node.attrs.title||'PDF 原文';remove.hidden=!editor.isEditable;open.href=src||'#';dom.dataset.src=src||'';
        if(src===source&&body)return;source=src;body?.remove();
        if(src&&new URL(src,location.origin).origin===location.origin){
          body=document.createElement('iframe');body.src='/static/pdf-viewer.html?v=20261030-reading-tools&file='+encodeURIComponent(new URL(src,location.origin).href);body.title='内嵌 PDF 阅读器';body.loading='lazy';body.referrerPolicy='no-referrer';
        }else{
          body=document.createElement('div');body.className='native-pdf-import';const hint=document.createElement('span');hint.textContent='请下载原文后，通过「插入 PDF」上传本地文件。';body.append(hint);
        }
        dom.append(body);
      };paint();
      return {dom,update(next){if(next.type!==node.type)return false;node=next;paint();return true;},stopEvent:event=>event.type!=='dragstart',ignoreMutation:()=>true};
    };},
  });
}

function documentReference(callbacks){
  return Node.create({
    name:'documentLink',group:'inline',inline:true,atom:true,selectable:true,
    addAttributes(){return {id:{default:0,parseHTML:el=>Number(el.getAttribute('data-document-id'))},title:{default:'',parseHTML:el=>el.getAttribute('data-title')||el.textContent}};},
    parseHTML(){return [{tag:'span[data-type="documentLink"]'}];},
    renderHTML({node}){return ['span',{'data-type':'documentLink','data-document-id':node.attrs.id,'data-title':node.attrs.title,class:'document-ref'},node.attrs.title];},
    markdownTokenName:'documentLink',
    markdownTokenizer:{name:'documentLink',level:'inline',start:source=>source.indexOf('[['),tokenize(source){const match=/^\[\[(\d+)\|([^\]\n]+)\]\]/.exec(source);if(match)return {type:'documentLink',raw:match[0],id:Number(match[1]),title:match[2]};}},
    parseMarkdown:token=>({type:'documentLink',attrs:{id:token.id,title:token.title}}),
    renderMarkdown:node=>'[['+node.attrs.id+'|'+String(node.attrs.title||'文档').replace(/[\]\n|]/g,'')+']]',
    addNodeView(){return ({node})=>{
      const dom=document.createElement('span');dom.className='document-ref native-reference';dom.contentEditable='false';dom.tabIndex=0;dom.setAttribute('role','link');
      const paint=()=>{dom.innerHTML=icon('document');dom.append(document.createTextNode(node.attrs.title||'文档'));dom.dataset.documentId=node.attrs.id;};paint();
      const open=event=>{event.preventDefault();event.stopPropagation();callbacks.openDocument?.(node.attrs.id);};dom.onclick=open;dom.onkeydown=event=>{if(event.key==='Enter')open(event);};
      return {dom,update(next){if(next.type!==node.type)return false;node=next;paint();return true;},stopEvent:()=>true,ignoreMutation:()=>true};
    };},
  });
}
export function researchNodes(callbacks){return [mathExtension('inlineMath',true,callbacks),mathExtension('blockMath',false,callbacks),latexBlockExtension(callbacks),pdfExtension(callbacks),documentReference(callbacks),SafeImage];}
