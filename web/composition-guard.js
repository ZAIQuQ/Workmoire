// ProseMirror can ask keyboard handlers about a Backspace inferred from an IME
// DOM deletion. Tiptap's list/core shortcuts may dispatch even when returning
// false. That empty transaction redraws stale text and ends Chrome's composition.
// Skip shortcut plugins during composition; native IME input and DOM parsing
// still run normally. Do not preventDefault or implement our own text buffer.
export function guardCompositionShortcuts(editor){
 const originals=[];
 for(const plugin of editor.state.plugins){
  const handler=plugin.props.handleKeyDown;if(!handler)continue;
  const guarded=(view,event)=>view.composing||event.isComposing||event.keyCode===229?false:handler.call(plugin,view,event);
  plugin.props.handleKeyDown=guarded;originals.push(()=>{if(plugin.props.handleKeyDown===guarded)plugin.props.handleKeyDown=handler;});
 }
 return ()=>originals.forEach(restore=>restore());
}
