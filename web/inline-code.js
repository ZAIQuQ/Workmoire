import {Code} from '@tiptap/extension-code';

function exitBoundary(editor,direction){
 const {selection,storedMarks,schema}=editor.state;
 if(!editor.isEditable||editor.view.composing||!selection.empty)return false;
 const code=schema.marks.code,{$from}=selection;
 const before=Boolean(code.isInSet($from.nodeBefore?.marks||[])),after=Boolean(code.isInSet($from.nodeAfter?.marks||[]));
 if(direction<0?before||!after:!before||after)return false;
 const marks=storedMarks||$from.marks();
 if(!code.isInSet(marks))return false;
 // Change only the typing format, without adding spacer characters to the document.
 editor.view.dispatch(editor.state.tr.setStoredMarks(code.removeFromSet(marks)));
 return true;
}

export const InlineCode=Code.extend({
 // At either boundary, ordinary text can be inserted without absorbing it into code.
 inclusive:false,
 exitable:false,
 addKeyboardShortcuts(){return {
  ...this.parent?.(),
  ArrowLeft:()=>exitBoundary(this.editor,-1),
  ArrowRight:()=>exitBoundary(this.editor,1),
 };},
});
