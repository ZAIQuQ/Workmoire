import {Extension} from '@tiptap/core';
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
 if(!editor.isEditable||editor.view.composing)return false;
 const next=validLineHeight(value);
 let selection=editor.state.selection;
 if(bookmark){try{selection=bookmark.mark.resolve(editor.state.doc);}catch{}bookmark.release?.();}
 const tr=editor.state.tr.setSelection(selection);
 const blocks=[];
 editor.state.doc.descendants((node,pos)=>{
  if(['paragraph','heading'].includes(node.type.name))blocks.push([node,pos]);
 });
 for(const [node,pos] of blocks){
  if(node.attrs.lineHeight!==next)tr.setNodeMarkup(pos,undefined,{...node.attrs,lineHeight:next},node.marks);
 }
 if(!tr.docChanged)return false;
 editor.view.dispatch(closeHistory(tr).scrollIntoView());
 editor.view.focus();
 return true;
}
