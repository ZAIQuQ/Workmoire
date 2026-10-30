import {Extension} from '@tiptap/core';
import {NodeSelection} from '@tiptap/pm/state';
import {closeHistory} from '@tiptap/pm/history';

export const LINE_HEIGHT_VALUES=['default','1','1.15','1.5','1.75','2'];
export const validLineHeight=value=>LINE_HEIGHT_VALUES.includes(value)?value:'default';

export const lineHeightExtension=Extension.create({
 name:'workmoireLineHeight',
 addGlobalAttributes(){return [{types:['paragraph','heading'],attributes:{lineHeight:{
  default:'default',
  parseHTML:element=>validLineHeight(element.getAttribute('data-line-height')),
  renderHTML:attrs=>{const value=validLineHeight(attrs.lineHeight);return value==='default'?{}:{'data-line-height':value,style:'line-height: '+value+';'};},
 }}}];},
});

export function applyLineHeight(editor,value,bookmark=null){
 if(!editor.isEditable||editor.view.composing||editor.state.selection instanceof NodeSelection)return false;
 const next=validLineHeight(value);
 let selection=editor.state.selection;
 if(bookmark){try{selection=bookmark.mark.resolve(editor.state.doc);}catch{}bookmark.release?.();}
 const {$from,from,to,empty}=selection;
 const tr=editor.state.tr.setSelection(selection);
 const blocks=new Map();
 const change=(node,pos)=>{
  if(node.attrs.lineHeight===next)return;
  tr.setNodeMarkup(pos,undefined,{...node.attrs,lineHeight:next},node.marks);
 };
 const rememberParent=resolved=>{if(['paragraph','heading'].includes(resolved.parent.type.name))blocks.set(resolved.before(resolved.depth),resolved.parent);};
 if(empty)rememberParent($from);
 else{
  rememberParent($from);rememberParent(selection.$to);
  editor.state.doc.nodesBetween(from,to,(node,pos)=>{
   if(['paragraph','heading'].includes(node.type.name)){blocks.set(pos,node);return false;}
   if(['codeBlock','table','bulletList','orderedList','taskList'].includes(node.type.name))return false;
  });
 }
 for(const [pos,node] of blocks)change(node,pos);
 if(!tr.docChanged)return false;
 editor.view.dispatch(closeHistory(tr).scrollIntoView());
 editor.view.focus();
 return true;
}
