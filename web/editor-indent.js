import {Extension} from '@tiptap/core';
import {NodeSelection,TextSelection} from '@tiptap/pm/state';
import {closeHistory} from '@tiptap/pm/history';

const MAX_INDENT=8,CODE_INDENT='    ';
const level=value=>Number.isInteger(value)&&value>=0&&value<=MAX_INDENT?value:0;

export const blockIndentExtension=Extension.create({
 name:'workmoireBlockIndent',
 addGlobalAttributes(){return [{types:['paragraph','heading'],attributes:{blockIndent:{
  default:0,
  parseHTML:element=>level(Number(element.getAttribute('data-block-indent'))),
  renderHTML:attrs=>level(attrs.blockIndent)?{'data-block-indent':String(attrs.blockIndent),style:'margin-inline-start: min('+attrs.blockIndent*2+'em, 45%);'}:{},
 }}}];},
});

function commit(editor,tr){
 if(!tr.docChanged)return;
 if(editor.state.storedMarks)tr.setStoredMarks(editor.state.storedMarks);
 editor.view.dispatch(closeHistory(tr).scrollIntoView());
}

function indentCode(editor,direction){
 const {selection}=editor.state,{$from,$to,from,to,empty}=selection;
 if(!$from.sameParent($to))return true;
 const tr=editor.state.tr,start=$from.start(),text=$from.parent.textContent;
 if(empty&&direction>0){tr.insertText(CODE_INDENT,from,to);commit(editor,tr);return true;}
 const relativeFrom=from-start,relativeTo=to-start;
 const first=relativeFrom===0?0:text.lastIndexOf('\n',relativeFrom-1)+1;
 const last=empty?relativeFrom:relativeTo>relativeFrom&&text[relativeTo-1]==='\n'?relativeTo-1:relativeTo;
 const edits=[];
 for(let offset=first;offset<=last;){
  const end=text.indexOf('\n',offset),line=text.slice(offset,end<0?undefined:end);
  if(direction>0)edits.push({pos:start+offset,remove:0,text:CODE_INDENT});
  else{const prefix=/^(?:\t| {1,4})/.exec(line)?.[0];if(prefix)edits.push({pos:start+offset,remove:prefix.length,text:''});}
  if(end<0||end>=last)break;offset=end+1;
 }
 for(const edit of edits.reverse())tr.insertText(edit.text,edit.pos,edit.pos+edit.remove);
 if(tr.docChanged)tr.setSelection(TextSelection.create(tr.doc,tr.mapping.map(selection.anchor),tr.mapping.map(selection.head)));
 commit(editor,tr);return true;
}

export function indentContent(editor,direction){
 if(!editor.isEditable||editor.view.composing||editor.state.selection instanceof NodeSelection)return false;
 const {selection,doc}=editor.state,{$from,from,to,empty}=selection;
 if($from.parent.type.name==='codeBlock')return indentCode(editor,direction);
 for(let depth=$from.depth;depth>0;depth--){
  const name=$from.node(depth).type.name;
  if(name==='listItem'||name==='taskItem'){
   const command=direction>0?'sinkListItem':'liftListItem';
   if(editor.can()[command](name))editor.commands[command](name);
   return true;
  }
 }
 const tr=editor.state.tr;
 const change=(node,pos)=>{const next=Math.max(0,Math.min(MAX_INDENT,level(node.attrs.blockIndent)+direction));if(next!==level(node.attrs.blockIndent))tr.setNodeMarkup(pos,undefined,{...node.attrs,blockIndent:next},node.marks);};
 if(empty&&['paragraph','heading'].includes($from.parent.type.name))change($from.parent,$from.before());
 else doc.nodesBetween(from,to,(node,pos)=>{
  if(['bulletList','orderedList','taskList','table','codeBlock'].includes(node.type.name))return false;
  if(['paragraph','heading'].includes(node.type.name)){if(pos+1!==to)change(node,pos);return false;}
 });
 commit(editor,tr);return true;
}

export function handleEditorTab(editor,event){
 if(event.key!=='Tab'||event.ctrlKey||event.metaKey||event.altKey||event.isComposing||event.keyCode===229||!editor.isEditable||editor.view.composing)return false;
 if(event.target?.closest?.('button,input,select,textarea,a,[contenteditable="false"]'))return false;
 // Table navigation takes precedence over paragraph/list indentation in a cell.
 if(editor.isActive('table')&&editor.state.selection.$from.parent.type.name!=='codeBlock'){
  if(event.shiftKey){if(editor.can().goToPreviousCell())editor.commands.goToPreviousCell();}
  else if(editor.can().goToNextCell())editor.commands.goToNextCell();
  else if(editor.can().addRowAfter())editor.chain().addRowAfter().goToNextCell().run();
  return true;
 }
 return indentContent(editor,event.shiftKey?-1:1);
}
