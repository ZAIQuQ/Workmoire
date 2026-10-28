import CodeBlockLowlight from '@tiptap/extension-code-block-lowlight';
import {Selection, TextSelection} from '@tiptap/pm/state';
import {closeHistory} from '@tiptap/pm/history';
import {codeTheme,toggleCodeTheme,onCodeThemeChange} from './code-theme.js';

const languages=[['','纯文本'],['python','Python'],['javascript','JavaScript'],['cpp','C / C++'],['json','JSON'],['sql','SQL'],['bash','Shell'],['xml','HTML / XML'],['css','CSS'],['latex','LaTeX']];
let nextId=0;
export function createCodeBlocks({lowlight,copy}){
 const views=new Set();
 const refresh=()=>views.forEach(view=>view.refresh());
 const unsubscribe=onCodeThemeChange(refresh);
 const extension=CodeBlockLowlight.extend({
  addAttributes(){return {...this.parent?.(),collapsed:{
   default:false,
   parseHTML:element=>element.getAttribute('data-collapsed')==='true',
   renderHTML:attrs=>attrs.collapsed?{'data-collapsed':'true'}:{},
  }};},
  addNodeView(){return ({node,getPos,editor})=>{
   // Only explicit editing actions write the attribute. Reading/search use an override.
   let override=null,scrollTop=0,scrollLeft=0,previousText=null;
   const dom=document.createElement('div');dom.className='native-code-block';
   const head=document.createElement('div');head.className='native-code-head';head.contentEditable='false';
   const makeButton=(cls,label,glyph)=>{
    const button=document.createElement('button');button.type='button';button.className=cls;
    button.setAttribute('aria-label',label);button.title=label;
    if(glyph)button.innerHTML=window.WorkmoireIcons.render(glyph);
    return button;
   };
   const fold=makeButton('code-fold','折叠代码','chevron');
   const language=document.createElement('select');language.setAttribute('aria-label','代码语言');
   for(const [value,label] of languages){const option=document.createElement('option');option.value=value;option.textContent=label;language.append(option);}
   const count=document.createElement('span');count.className='code-line-count';
   const theme=makeButton('code-theme','切换代码配色');theme.onclick=toggleCodeTheme;
   const copyButton=makeButton('code-copy','复制完整代码','copy');copyButton.onclick=()=>copy?.(node.textContent);
   const pre=document.createElement('pre'),code=document.createElement('code');pre.id='workmoire-code-'+(++nextId);pre.append(code);fold.setAttribute('aria-controls',pre.id);
   const preview=makeButton('code-fold-preview','展开代码');preview.contentEditable='false';preview.setAttribute('aria-controls',pre.id);
   head.append(fold,language,count,theme,copyButton);dom.append(head,preview,pre);
   const collapsed=()=>override??node.attrs.collapsed;
   function refresh(){
    const hidden=collapsed();
    if(pre.hidden!==hidden){
     if(hidden){scrollTop=pre.scrollTop;scrollLeft=pre.scrollLeft;}
     pre.hidden=hidden;
     if(!hidden){pre.scrollTop=scrollTop;pre.scrollLeft=scrollLeft;}
    }
    preview.hidden=!hidden;dom.dataset.collapsed=String(hidden);fold.setAttribute('aria-expanded',String(!hidden));
    const label=hidden?'展开代码':'折叠代码';fold.title=label;fold.setAttribute('aria-label',label);
    language.disabled=!editor.isEditable;
    const value=node.attrs.language||'';
    if(!Array.from(language.options).some(option=>option.value===value)){const option=document.createElement('option');option.value=value;option.textContent=value;language.append(option);}
    language.value=value;
    const dark=codeTheme()==='dark',themeLabel=dark?'使用浅色代码配色':'使用深色代码配色';
    theme.title=themeLabel;theme.setAttribute('aria-label',themeLabel);theme.setAttribute('aria-pressed',String(dark));
    if(theme.dataset.theme!==codeTheme()){theme.innerHTML=window.WorkmoireIcons.render(dark?'sun':'moon');theme.dataset.theme=codeTheme();}
    if(previousText!==node.textContent){
     previousText=node.textContent;count.textContent=(previousText.split('\n').length)+' 行';
     preview.textContent=previousText.split('\n').find(line=>line.trim())?.trim().slice(0,200)||'空代码块';
    }
   }
   function moveHiddenCaret(tr,pos){
    const selection=tr.selection;
    if(selection instanceof TextSelection&&selection.from>pos&&selection.to<pos+node.nodeSize){
     const next=Selection.findFrom(tr.doc.resolve(pos+node.nodeSize),1,true)||Selection.findFrom(tr.doc.resolve(pos),-1,true);
     if(next)tr.setSelection(next);
    }
    return tr;
   }
   function toggle(){
    const pos=getPos();if(typeof pos!=='number')return;
    const next=!collapsed();let tr=editor.state.tr;
    if(next)tr=moveHiddenCaret(tr,pos);
    if(editor.isEditable&&next!==node.attrs.collapsed){
     override=null;tr=closeHistory(tr).setNodeMarkup(pos,undefined,{...node.attrs,collapsed:next});
     editor.view.dispatch(tr);editor.view.dispatch(closeHistory(editor.state.tr));
    }else{
     override=next;refresh();if(tr.selectionSet)editor.view.dispatch(tr);
    }
   }
   fold.onclick=toggle;preview.onclick=toggle;
   // Mouse buttons keep the editor caret; keyboard activation keeps button focus.
   head.onmousedown=event=>{if(event.target.closest('button'))event.preventDefault();};
   preview.onmousedown=event=>event.preventDefault();
   language.onchange=()=>{const pos=getPos();if(editor.isEditable&&typeof pos==='number')editor.view.dispatch(editor.state.tr.setNodeMarkup(pos,undefined,{...node.attrs,language:language.value||null}));};
   const controller={refresh,reveal(selection){
    if(!collapsed()||!(selection instanceof TextSelection))return;
    const pos=getPos();
    // Whole-document / cross-block selections must not expand every folded block.
    if(typeof pos==='number'&&selection.from>pos&&selection.to<pos+node.nodeSize){override=false;refresh();}
   }};
   views.add(controller);refresh();
   return {
    dom,contentDOM:code,
    update(updated){
     if(updated.type!==node.type)return false;
     if(updated.attrs.collapsed!==node.attrs.collapsed)override=null;
     node=updated;refresh();return true;
    },
    stopEvent:event=>head.contains(event.target)||preview.contains(event.target),
    ignoreMutation:mutation=>head.contains(mutation.target)||preview.contains(mutation.target)||mutation.type==='attributes'&&(mutation.target===dom||mutation.target===pre),
    destroy(){views.delete(controller);},
   };
  };},
 }).configure({lowlight,defaultLanguage:null,exitOnTripleEnter:true,exitOnArrowDown:true});
 return {extension,refresh,reveal:selection=>views.forEach(view=>view.reveal(selection)),destroy:unsubscribe};
}
