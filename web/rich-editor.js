import {blockIndentExtension,handleEditorTab,indentContent} from './editor-indent.js';
import {InlineCode} from './inline-code.js';
import {guardCompositionShortcuts} from './composition-guard.js';
import {DocumentTable,equalizeColumns,toggleTableWidth,selectedTable} from './document-table.js';
import {DocumentFontStep,documentFontExtension,documentFontKey,validBodyFont} from './document-font.js';
import {Editor, Extension} from '@tiptap/core';
import StarterKit from '@tiptap/starter-kit';
import {Markdown} from '@tiptap/markdown';
import {TableKit} from '@tiptap/extension-table';
import TaskList from '@tiptap/extension-task-list';
import TaskItem from '@tiptap/extension-task-item';
import TextAlign from '@tiptap/extension-text-align';
import Highlight from '@tiptap/extension-highlight';
import {TextStyle, Color} from '@tiptap/extension-text-style';
import Subscript from '@tiptap/extension-subscript';
import Superscript from '@tiptap/extension-superscript';
import Placeholder from '@tiptap/extension-placeholder';
import {BubbleMenu} from '@tiptap/extension-bubble-menu';
import {DragHandle} from '@tiptap/extension-drag-handle';
import {createCodeBlocks} from './code-block.js';
import {Plugin, PluginKey, TextSelection, NodeSelection} from '@tiptap/pm/state';
import {Fragment} from '@tiptap/pm/model';
import {closeHistory} from '@tiptap/pm/history';
import {pdfCitation,pdfViewerURL} from './pdf-source.js';
import {Decoration, DecorationSet} from '@tiptap/pm/view';
import {createLowlight} from 'lowlight';
import javascript from 'highlight.js/lib/languages/javascript';
import python from 'highlight.js/lib/languages/python';
import cpp from 'highlight.js/lib/languages/cpp';
import json from 'highlight.js/lib/languages/json';
import sql from 'highlight.js/lib/languages/sql';
import bash from 'highlight.js/lib/languages/bash';
import xml from 'highlight.js/lib/languages/xml';
import css from 'highlight.js/lib/languages/css';
import latex from 'highlight.js/lib/languages/latex';
import {researchNodes,safeLink,SafeLink,safeMarkdownParser} from './rich-extensions.js';
import {safeMedia,mathHTML} from './markdown-preview.js';
import {searchSlashCommands} from './slash-commands.mjs';

const lowlight=createLowlight({javascript,python,cpp,json,sql,bash,xml,css,latex});
const icon=name=>window.WorkmoireIcons.render(name);
function button(command,label,glyph){const el=document.createElement('button');el.type='button';el.dataset.richCommand=command;el.title=label;el.setAttribute('aria-label',label);el.innerHTML=icon(glyph);return el;}
function positionMenu(menu,anchor,maxHeight=350){
 const width=Math.min(menu.offsetWidth||270,innerWidth-24),availableBelow=innerHeight-anchor.bottom-14,above=anchor.top-14;
 const upward=availableBelow<Math.min(maxHeight,220)&&above>availableBelow;
 menu.style.maxHeight=Math.max(100,Math.min(maxHeight,upward?above:availableBelow))+'px';
 menu.style.left=Math.max(12,Math.min(anchor.left,innerWidth-width-12))+'px';
 menu.style.top=(upward?Math.max(12,anchor.top-menu.offsetHeight-6):anchor.bottom+6)+'px';
}
function findText(doc,query){
 if(!query)return [];
 const matches=[],pattern=query.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
 doc.descendants((node,pos)=>{
  if(!node.isTextblock)return;
  let text='',positions=[];
  node.forEach((child,offset)=>{if(child.isText){text+=child.text;for(let i=0;i<child.text.length;i++)positions.push(pos+1+offset+i);}else{text+='\ufffc';positions.push(pos+1+offset);}});
  const matcher=new RegExp(pattern,'giu');let match;
  while((match=matcher.exec(text))&&matches.length<1000)matches.push({from:positions[match.index],to:positions[match.index+match[0].length-1]+1});
  return false;
 });
 return matches;
}

export function mountRichEditor(host,options={}){
 let editor,ready=false,destroyed=false,markdownCache='',cachedDoc=null,baselineDoc=null,baselineMarkdown=options.baseline?.content??options.content??'',slashRange=null,slashIndex=0,slashItems=[],blockTarget=null,updateFrame=0,blurTimer=0,compositionTimer=0;
 const reservations=new Set(),owned=[],cleanup=[],diagnostics={markdownSerializations:0,documentUpdates:0};
 const make=(tag,cls,parent=host)=>{const node=document.createElement(tag);node.className=cls;parent.append(node);return node;};
 const scroll=make('div','rich-editor-scroll');const contentHost=make('div','rich-editor-content',scroll);
 const bubble=document.createElement('div');bubble.className='rich-bubble-menu';owned.push(bubble);bubble.setAttribute('role','toolbar');bubble.setAttribute('aria-label','选中文字格式');
 for(const item of [['bold','加粗','bold'],['italic','斜体','italic'],['underline','下划线','underline'],['strike','删除线','strike'],['highlight','高亮','highlight'],['link','链接','link'],['inline-math','行内公式','variable']])bubble.append(button(...item));
 bubble.addEventListener('mousedown',event=>event.preventDefault());bubble.addEventListener('click',event=>{const target=event.target.closest('[data-rich-command]');if(target)run(target.dataset.richCommand);});
 const slash=make('div','rich-slash-menu',document.body);owned.push(slash);slash.hidden=true;slash.setAttribute('role','listbox');slash.setAttribute('aria-label','插入内容块');
 const blockMenu=make('div','rich-block-menu',document.body);owned.push(blockMenu);blockMenu.hidden=true;blockMenu.setAttribute('role','menu');
 for(const [action,label,glyph] of [['move-up','上移','up'],['move-down','下移','down'],['duplicate','复制块','copy'],['delete-block','删除块','trash']]){
   const el=button(action,label,glyph);el.append(document.createTextNode(label));el.setAttribute('role','menuitem');blockMenu.append(el);
 }
 blockMenu.onmousedown=event=>event.preventDefault();blockMenu.onclick=event=>{const action=event.target.closest('[data-rich-command]')?.dataset.richCommand;if(action)blockAction(action);};
 const findbar=make('div','rich-findbar');findbar.hidden=true;
 const findInput=document.createElement('input');findInput.type='search';findInput.placeholder='查找当前文档';findInput.setAttribute('aria-label','查找当前文档');
 const findCount=document.createElement('span');findCount.setAttribute('role','status');
 const previous=button('find-previous','上一处','previous'),next=button('find-next','下一处','next'),closeFind=button('find-close','关闭查找','close');findbar.append(findInput,findCount,previous,next,closeFind);
 let findQuery='',findIndex=0,findMatches=[];const findKey=new PluginKey('workmoireFind');
 const SearchExtension=Extension.create({name:'documentSearch',addProseMirrorPlugins(){return [new Plugin({key:findKey,state:{
  init:()=>DecorationSet.empty,
  apply(tr,decorations){
   if(tr.getMeta(findKey)||tr.docChanged&&findQuery){
    findMatches=findText(tr.doc,findQuery);findIndex=Math.min(findIndex,Math.max(0,findMatches.length-1));
    findCount.textContent=findMatches.length?(findIndex+1)+' / '+findMatches.length:'0 / 0';
    return DecorationSet.create(tr.doc,findMatches.map((match,i)=>Decoration.inline(match.from,match.to,{class:i===findIndex?'rich-find-current':'rich-find-match'})));
   }
   return tr.docChanged?decorations.map(tr.mapping,tr.doc):decorations;
  }
 },props:{decorations:state=>findKey.getState(state)}})];}});
 function search(direction=0){
  findQuery=findInput.value;findMatches=findText(editor.state.doc,findQuery);
  if(direction&&findMatches.length)findIndex=(findIndex+direction+findMatches.length)%findMatches.length;else findIndex=0;
  let tr=editor.state.tr.setMeta(findKey,true);
  if(findMatches.length){const match=findMatches[findIndex],selection=TextSelection.create(tr.doc,match.from,match.to);codeBlocks.reveal(selection);tr=tr.setSelection(selection).scrollIntoView();}
  editor.view.dispatch(tr);
  // The find input owns DOM focus; ProseMirror alone may skip the code's scroller.
  editor.view.dom.querySelector('.rich-find-current')?.scrollIntoView({block:'nearest',inline:'nearest'});
 }
 findInput.oninput=()=>search();findInput.onkeydown=event=>{if(event.isComposing)return;if(event.key==='Enter'){event.preventDefault();search(event.shiftKey?-1:1);}if(event.key==='Escape')hideFind();};previous.onclick=()=>search(-1);next.onclick=()=>search(1);closeFind.onclick=()=>hideFind();
 function hideFind(){findbar.hidden=true;findQuery='';findInput.value='';editor.view.dispatch(editor.state.tr.setMeta(findKey,true));editor.commands.focus();}

 const codeBlocks=createCodeBlocks({lowlight,copy:options.copy});cleanup.push(codeBlocks.destroy);
 const callbacks={math:openMath,openDocument:id=>options.openDocument?.(id)};
 const NativeKeys=Extension.create({name:'workmoireKeys',addKeyboardShortcuts(){return {
  'Mod-Shift-x':()=>editor.commands.toggleTaskList(),
  'Mod-Shift-h':()=>editor.commands.toggleHighlight({color:'#fff2a8'}),
  'Mod-Alt-0':()=>editor.commands.setParagraph(),
  'Mod-f':()=>{showFind();return true;},
 };}});
 const initialFont=validBodyFont(options.richContent?.document?.attrs?.bodyFont);
 let baselineFont=options.baseline?validBodyFont(options.baseline.rich_content?.document?.attrs?.bodyFont):initialFont,lastFont=initialFont;
 const bodyFont=()=>documentFontKey.getState(editor.state)||'sans';
 const initialNative=options.richContent?.version===1?options.richContent.document:null;
 editor=new Editor({
  element:contentHost,
  content:initialNative||options.content||'',contentType:initialNative?'json':'markdown',editable:options.editable!==false,enableContentCheck:true,
  extensions:[
   StarterKit.configure({code:false,codeBlock:false,link:false}),InlineCode,SafeLink,blockIndentExtension,documentFontExtension(initialFont),
   Markdown.configure({marked:safeMarkdownParser(),markedOptions:{gfm:true,breaks:true},indentation:{style:'space',size:2}}),
   TableKit.configure({table:false}),DocumentTable,TaskList,TaskItem.configure({nested:true,HTMLAttributes:{'data-type':'taskItem'},a11y:{checkboxLabel:node=>'切换待办：'+(node.textContent||'空白任务')}}),
   TextAlign.configure({types:['heading','paragraph']}),TextStyle,Color,Highlight.configure({multicolor:true}),Subscript,Superscript,
   Placeholder.configure({placeholder:({node})=>node.type.name==='heading'?'标题':'输入 / 插入内容',showOnlyCurrent:true,includeChildren:false}),
   ...researchNodes(callbacks),codeBlocks.extension,SearchExtension,NativeKeys,
   BubbleMenu.configure({element:bubble,appendTo:()=>document.body,updateDelay:80,options:{placement:'top',offset:8},shouldShow:({editor:instance,state})=>instance.isEditable&&!state.selection.empty&&!(state.selection instanceof NodeSelection)&&!instance.isActive('codeBlock')&&!instance.isActive('table')}),
   DragHandle.configure({render(){
    const handle=document.createElement('div');handle.className='rich-block-handle';handle.setAttribute('aria-label','内容块操作');
    const add=button('add-block','在下方插入内容','plus'),grip=button('block-menu','拖动或管理内容块','grip');grip.dataset.dragHandle='';
    add.onmousedown=event=>{event.preventDefault();event.stopPropagation();};add.onclick=event=>{event.preventDefault();event.stopPropagation();if(blockTarget){const at=blockTarget.pos+blockTarget.node.nodeSize;editor.chain().focus().insertContentAt(at,{type:'paragraph',content:[{type:'text',text:'/'}]}).setTextSelection(at+2).run();}};
    grip.onclick=event=>{event.preventDefault();event.stopPropagation();if(blockTarget&&editor.isEditable){blockMenu.hidden=false;positionMenu(blockMenu,grip.getBoundingClientRect(),240);}};
    handle.append(add,grip);return handle;
   },onElementDragStart:()=>editor.view.dispatch(closeHistory(editor.state.tr)),onElementDragEnd:()=>editor.view.dispatch(closeHistory(editor.state.tr)),nested:false,dragImageProperties:['color','background-color','font-size','font-family','padding'],onNodeChange:({node,pos})=>{blockTarget=node?{node,pos}:null;},computePositionConfig:{placement:'left-start',strategy:'absolute'}}),
  ],
  editorProps:{
   attributes:state=>({'data-body-font':documentFontKey.getState(state)||'sans',class:'rich-document prose','aria-label':'文档正文','aria-multiline':'true',role:'textbox',spellcheck:'false'}),
   handleDOMEvents:{compositionstart(){hideSlash();return false;},compositionend(){clearTimeout(compositionTimer);compositionTimer=setTimeout(()=>{if(!destroyed)scheduleControls();},20);return false;}},
   handleKeyDown(view,event){
    if(event.isComposing||view.composing||event.keyCode===229)return false;
    if(!slash.hidden&&slashRange){
     if(['ArrowDown','ArrowUp','Enter','Escape'].includes(event.key)){
      event.preventDefault();if(event.key==='Escape'){hideSlash();return true;}
      if(event.key==='Enter'){chooseSlash(slashIndex);return true;}
      slashIndex=(slashIndex+(event.key==='ArrowDown'?1:-1)+slashItems.length)%slashItems.length;paintSlash();return true;
     }
    }
    if(handleEditorTab(editor,event)){hideSlash();return true;}
    if(event.key==='Escape'&&editor.isEditable&&event.target===view.dom){view.dom.closest('.document-editor')?.querySelector('#heading-tool')?.focus();}
    return false;
   },
   handlePaste(view,event){
    const files=Array.from(event.clipboardData?.files||[]).filter(file=>file.type.startsWith('image/')||file.type==='application/pdf');
    if(files.length){event.preventDefault();for(const file of files)options.upload?.(file,createBookmark());return true;}
    const html=event.clipboardData?.getData('text/html'),text=event.clipboardData?.getData('text/plain')||'';
    if(!html&&!editor.isActive('codeBlock')&&/^(?:#{1,6}\s|>\s|```|\$\$|[-*+]\s|\d+\.\s|\|.+\|)|!\[[^\]]*\]\(|@\[pdf\]\(/m.test(text)){
     event.preventDefault();editor.commands.insertContent(text,{contentType:'markdown'});return true;
    }
    return false;
   },
   handleDrop(view,event,slice,moved){
    if(moved||!event.dataTransfer?.files?.length)return false;
    event.preventDefault();const coords=view.posAtCoords({left:event.clientX,top:event.clientY});if(coords)editor.commands.setTextSelection(coords.pos);
    for(const file of Array.from(event.dataTransfer.files))options.upload?.(file,createBookmark());return true;
   },
   handleClick(view,pos,event){const anchor=event.target.closest('a[href]');if(anchor){const href=safeLink(anchor.getAttribute('href'));if(href&&!pdfCitation(href)&&(!editor.isEditable||event.metaKey||event.ctrlKey)){event.preventDefault();window.open(href,'_blank','noopener,noreferrer');return true;}}return false;},
  },
  onTransaction({transaction}){if(ready&&transaction.storedMarksSet)scheduleControls();for(const reservation of reservations)reservation.mark=reservation.mark.map(transaction.mapping);if(ready&&bodyFont()!==lastFont){lastFont=bodyFont();options.onChange?.();scheduleControls();}},
  onUpdate({transaction}){if(ready&&transaction.docChanged){diagnostics.documentUpdates++;options.onChange?.();scheduleControls();}},
  onSelectionUpdate(){if(ready){codeBlocks.reveal(editor.state.selection);scheduleControls();}},
  onBlur(){clearTimeout(blurTimer);blurTimer=setTimeout(()=>{if(destroyed)return;if(!slash.contains(document.activeElement))hideSlash();if(!bubble.contains(document.activeElement))editor.view.dispatch(editor.state.tr.setMeta('bubbleMenu','hide'));},120);},
 });
 cleanup.push(guardCompositionShortcuts(editor));
 const citationClick=event=>{const anchor=event.target.closest('a[href]'),citation=anchor&&pdfCitation(anchor.getAttribute('href'));if(!citation)return;event.preventDefault();event.stopPropagation();if(event.metaKey||event.ctrlKey||!options.openPDF?.(citation))window.open(pdfViewerURL(citation,citation.page),'_blank','noopener,noreferrer');};
 host.addEventListener('click',citationClick,true);cleanup.push(()=>host.removeEventListener('click',citationClick,true));
 function completeDocument(doc){return doc.lastChild?.type.name==='paragraph'?doc:doc.copy(doc.content.append(Fragment.from(editor.schema.nodes.paragraph.create())));}
 function parseDocument(markdown){return completeDocument(editor.schema.nodeFromJSON(editor.markdown.parse(markdown||'')));}
 if(editor.state.doc.lastChild?.type.name!=='paragraph')editor.view.dispatch(editor.state.tr.insert(editor.state.doc.content.size,editor.schema.nodes.paragraph.create()).setMeta('addToHistory',false));
 const baselineNative=options.baseline?.rich_content?.version===1?options.baseline.rich_content.document:null;
 baselineDoc=baselineNative?completeDocument(editor.schema.nodeFromJSON(baselineNative)):parseDocument(baselineMarkdown);
 markdownCache=options.content||'';cachedDoc=editor.state.doc;ready=true;
 function scheduleControls(){cancelAnimationFrame(updateFrame);updateFrame=requestAnimationFrame(()=>{if(!destroyed){updateSlash();updateBubble();options.onSelection?.();}});}
 function updateBubble(){for(const el of bubble.querySelectorAll('[data-rich-command]'))el.classList.toggle('is-active',isActive(el.dataset.richCommand));}
 function hideSlash(){slash.hidden=true;slashRange=null;editor.view.dom.removeAttribute('aria-activedescendant');}
 function updateSlash(){
  if(!editor.isEditable||editor.view.composing||!editor.state.selection.empty){hideSlash();return;}
  const {$from}=editor.state.selection;if($from.parent.type.name!=='paragraph'){hideSlash();return;}
  const prefix=$from.parent.textBetween(0,$from.parentOffset,'','\ufffc'),match=/^[\/／]([^\/／\r\n]{0,64})$/u.exec(prefix);
  if(!match){hideSlash();return;}
  const query=match[1];slashItems=searchSlashCommands(query);
  if(!slashItems.length){hideSlash();return;}
  const range={from:$from.start(),to:$from.pos,query};if(slashRange?.query!==query)slashIndex=0;slashRange=range;slashIndex=Math.min(slashIndex,slashItems.length-1);paintSlash();
 }
 function paintSlash(){
  slash.replaceChildren();const caption=document.createElement('div');caption.className='rich-menu-caption';caption.textContent='插入内容 · 中文 / 简拼 / 英文';slash.append(caption);
  slashItems.forEach((item,index)=>{const el=document.createElement('button');el.type='button';el.id='rich-slash-option-'+index;el.className=index===slashIndex?'is-active':'';el.setAttribute('role','option');el.setAttribute('aria-selected',String(index===slashIndex));el.dataset.commandId=item.id;el.innerHTML=icon(item.icon);const text=document.createElement('span'),label=document.createElement('strong'),description=document.createElement('small');label.textContent=item.label;description.textContent=item.description;text.append(label,description);const shortcut=document.createElement('kbd');shortcut.textContent=item.shortcut;el.append(text,shortcut);el.onmousedown=event=>event.preventDefault();el.onclick=()=>chooseSlash(index);slash.append(el);});
  slash.hidden=false;const coords=editor.view.coordsAtPos(editor.state.selection.from);positionMenu(slash,coords);editor.view.dom.setAttribute('aria-activedescendant','rich-slash-option-'+slashIndex);slash.querySelector('[aria-selected="true"]')?.scrollIntoView({block:'nearest'});
 }
 function chooseSlash(index){const item=slashItems[index],range=slashRange;if(!item||!range)return;hideSlash();editor.chain().focus().deleteRange({from:range.from,to:range.to}).run();run(item.id);}
 const outside=event=>{if(!slash.contains(event.target)&&!editor.view.dom.contains(event.target))hideSlash();if(!blockMenu.contains(event.target)&&!event.target.closest('.rich-block-handle'))blockMenu.hidden=true;};document.addEventListener('mousedown',outside);cleanup.push(()=>document.removeEventListener('mousedown',outside));
 const reflow=()=>{hideSlash();blockMenu.hidden=true;};scroll.addEventListener('scroll',reflow);window.addEventListener('resize',reflow);cleanup.push(()=>window.removeEventListener('resize',reflow));
 function createBookmark(){const reservation={mark:editor.state.selection.getBookmark(),release(){reservations.delete(reservation);}};reservations.add(reservation);return reservation;}
 function insertAtReservation(value,reservation){
  let chain=editor.chain().focus();if(reservation&&reservations.has(reservation)){try{const selection=reservation.mark.resolve(editor.state.doc);chain=chain.command(({tr})=>{tr.setSelection(selection);return true;});}catch{}reservation.release();}
  const result=chain.insertContent(value).run();
  const selection=editor.state.selection;
  if(selection instanceof NodeSelection&&selection.node.isBlock){const pos=Math.min(selection.to+1,editor.state.doc.content.size);editor.commands.setTextSelection(pos);}
  return result;
 }
 function blockAction(action){
  blockMenu.hidden=true;if(!blockTarget||!editor.isEditable)return;
  const {pos}=blockTarget,node=editor.state.doc.nodeAt(pos);if(!node)return;
  editor.view.dispatch(closeHistory(editor.state.tr));
  const doc=editor.state.doc,index=doc.resolve(pos).index(0);
  if(action==='delete-block'){editor.chain().focus().deleteRange({from:pos,to:pos+node.nodeSize}).run();editor.view.dispatch(closeHistory(editor.state.tr));return;}
  if(action==='duplicate'){editor.chain().focus().insertContentAt(pos+node.nodeSize,node.toJSON()).run();editor.view.dispatch(closeHistory(editor.state.tr));return;}
  const target=action==='move-up'?index-1:index+1;if(target<0||target>=doc.childCount)return;
  let destination=0;for(let i=0;i<(action==='move-up'?target:target+1);i++)destination+=doc.child(i).nodeSize;
  const tr=editor.state.tr.delete(pos,pos+node.nodeSize);if(destination>pos)destination-=node.nodeSize;tr.insert(destination,node);tr.setSelection(NodeSelection.create(tr.doc,destination)).scrollIntoView();editor.view.dispatch(tr);editor.view.dispatch(closeHistory(editor.state.tr));editor.commands.focus();
 }
 function dialogShell(title){
  const dialog=document.createElement('dialog');dialog.className='dialog native-editor-dialog';const form=document.createElement('form');form.className='dialog-card';
  const head=document.createElement('div');head.className='dialog-head';const heading=document.createElement('h2');heading.textContent=title;const close=button('close','关闭','close');close.className='icon-button';close.onclick=()=>dialog.close();head.append(heading,close);form.append(head);dialog.append(form);document.body.append(dialog);owned.push(dialog);
  dialog.addEventListener('close',()=>{dialog.remove();const i=owned.indexOf(dialog);if(i>=0)owned.splice(i,1);});dialog.addEventListener('click',event=>{if(event.target===dialog){const r=dialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)dialog.close();}});
  return {dialog,form};
 }
 function openMath(spec={inline:false}){
  if(!editor.isEditable)return;
  const reservation=spec.node?null:createBookmark();const {dialog,form}=dialogShell(spec.inline?'行内公式':'块级公式');dialog.classList.add('math-dialog');
  const label=document.createElement('label');label.className='field';const title=document.createElement('span');title.textContent='LaTeX 公式';const field=document.createElement('textarea');field.rows=4;field.maxLength=10000;field.setAttribute('aria-label','LaTeX 公式');field.value=spec.node?.attrs.latex||editor.state.doc.textBetween(editor.state.selection.from,editor.state.selection.to,' ')||(spec.inline?'\\alpha + \\beta':'E = mc^2');label.append(title,field);
  const preview=document.createElement('div');preview.className='math-dialog-preview';const paint=()=>{preview.innerHTML=mathHTML(field.value,!spec.inline);};field.oninput=paint;paint();const actions=document.createElement('div');actions.className='dialog-actions';const submit=document.createElement('button');submit.className='button primary';submit.type='submit';submit.textContent=spec.node?'更新公式':'插入公式';actions.append(submit);form.append(label,preview,actions);
  form.onsubmit=event=>{event.preventDefault();const latex=field.value.trim();if(!latex)return;if(spec.node){const pos=spec.getPos?.();if(typeof pos==='number'&&editor.state.doc.nodeAt(pos)?.type===spec.node.type)editor.view.dispatch(editor.state.tr.setNodeMarkup(pos,undefined,{latex}));}else insertAtReservation({type:spec.inline?'inlineMath':'blockMath',attrs:{latex}},reservation);dialog.close();editor.commands.focus();};dialog.addEventListener('close',()=>reservation?.release());dialog.showModal();field.focus();field.select();
 }
 function openLink(){
  if(!editor.isEditable)return;
  if(editor.isActive('link'))editor.commands.extendMarkRange('link');const reservation=createBookmark();const selection=editor.state.selection;const selected=editor.state.doc.textBetween(selection.from,selection.to,' ');
  const {dialog,form}=dialogShell('编辑链接');dialog.classList.add('native-link-dialog');
  const fields=[];for(const [label,value,name] of [['显示文字',selected,'链接文字'],['链接地址',editor.getAttributes('link').href||'','链接地址']]){const wrapper=document.createElement('label');wrapper.className='field';const caption=document.createElement('span');caption.textContent=label;const input=document.createElement('input');input.value=value;input.setAttribute('aria-label',name);input.maxLength=name==='链接地址'?3000:10000;wrapper.append(caption,input);form.append(wrapper);fields.push(input);}
  fields[1].placeholder='https://…';const error=document.createElement('p');error.className='error';error.setAttribute('role','alert');form.append(error);const actions=document.createElement('div');actions.className='dialog-actions';
  const remove=document.createElement('button');remove.type='button';remove.className='button secondary';remove.textContent='移除链接';remove.onclick=()=>{editor.chain().focus().extendMarkRange('link').unsetLink().run();dialog.close();};
  const submit=document.createElement('button');submit.type='submit';submit.className='button primary';submit.textContent='应用链接';actions.append(remove,submit);form.append(actions);
  form.onsubmit=event=>{event.preventDefault();let raw=fields[1].value.trim();if(!/^[a-z][a-z\d+.-]*:|^[\/#]/i.test(raw))raw='https://'+raw;const href=safeLink(raw);if(!href){error.textContent='请输入有效的 HTTP、HTTPS 或邮件链接。';return;}let range;try{range=reservation.mark.resolve(editor.state.doc);}catch{range=editor.state.selection;}const label=fields[0].value||href;editor.chain().focus().setTextSelection({from:range.from,to:range.to}).insertContent({type:'text',text:label,marks:[{type:'link',attrs:{href,target:'_blank',rel:'noopener noreferrer nofollow'}}]}).run();dialog.close();};dialog.addEventListener('close',()=>reservation.release());dialog.showModal();fields[1].focus();
 }
 function run(command){
  if(!editor.isEditable&&command!=='find')return false;
  const chain=()=>editor.chain().focus();
  if(command.startsWith('heading-'))return chain().toggleHeading({level:Number(command.slice(-1))}).run();
  switch(command){
   case 'paragraph':return chain().setParagraph().run();
   case 'bold':return chain().toggleBold().run();case 'italic':return chain().toggleItalic().run();case 'underline':return chain().toggleUnderline().run();case 'strike':return chain().toggleStrike().run();case 'inline-code':return chain().toggleCode().run();
   case 'highlight':return chain().toggleHighlight({color:'#fff2a8'}).run();case 'clear-format':return chain().unsetAllMarks().run();
   case 'list':return chain().toggleBulletList().run();case 'ordered-list':return chain().toggleOrderedList().run();case 'task':return chain().toggleTaskList().run();case 'quote':return chain().toggleBlockquote().run();
   case 'code':return chain().toggleCodeBlock({language:'python'}).run();case 'table':return chain().insertTable({rows:3,cols:3,withHeaderRow:true}).run();case 'divider':return chain().setHorizontalRule().run();
   case 'formula':openMath({inline:false});return true;case 'inline-math':openMath({inline:true});return true;case 'link':openLink();return true;
   case 'undo':return chain().undo().run();case 'redo':return chain().redo().run();
   case 'align-left':case 'align-center':case 'align-right':return chain().setTextAlign(command.slice(6)).run();
   case 'subscript':return chain().toggleSubscript().run();case 'superscript':return chain().toggleSuperscript().run();
   case 'indent':editor.commands.focus();return indentContent(editor,1);case 'outdent':editor.commands.focus();return indentContent(editor,-1);
   case 'equal-columns':return equalizeColumns(editor);case 'table-fixed-width':return toggleTableWidth(editor);
   case 'row-before':return chain().addRowBefore().run();case 'row-after':return chain().addRowAfter().run();case 'column-before':return chain().addColumnBefore().run();case 'column-after':return chain().addColumnAfter().run();
   case 'delete-row':return chain().deleteRow().run();case 'delete-column':return chain().deleteColumn().run();case 'delete-table':return chain().deleteTable().run();case 'table-header':return chain().toggleHeaderRow().run();case 'merge-cells':return chain().mergeCells().run();case 'split-cell':return chain().splitCell().run();
   case 'find':showFind();return true;
   default:if(['image','pdf','document-link','symbols'].includes(command)){options.command?.(command);return true;}return false;
  }
 }
 function isActive(command){if(command.startsWith('align-')){const alignment=command.slice(6);return editor.isActive({textAlign:alignment})||(alignment==='left'&&!['center','right','justify'].some(value=>editor.isActive({textAlign:value})));}const mapping={list:'bulletList','ordered-list':'orderedList',task:'taskList',quote:'blockquote',code:'codeBlock','inline-code':'code'};return editor.isActive(mapping[command]||command);}
 function showFind(){findbar.hidden=false;findInput.focus();findInput.select();}
 const adapter={
  tiptap:editor,view:editor.view,diagnostics,
  getValue(){const doc=editor.state.doc;if(doc===cachedDoc)return markdownCache;if(doc.eq(baselineDoc)){markdownCache=baselineMarkdown;}else{markdownCache=editor.getMarkdown();diagnostics.markdownSerializations++;}cachedDoc=doc;return markdownCache;},
  getNative:()=>({version:1,document:{...editor.getJSON(),attrs:{bodyFont:bodyFont()}}}),
  getText:()=>editor.state.doc.textBetween(0,editor.state.doc.content.size,'\n'),
  hasChanges:()=>!editor.state.doc.eq(baselineDoc)||bodyFont()!==baselineFont,
  isEmpty:()=>editor.isEmpty,
  isComposing:()=>editor.view.composing,
  markBaseline(item){baselineFont=validBodyFont(item.rich_content?.document?.attrs?.bodyFont);baselineMarkdown=item.content||'';baselineDoc=item.rich_content?.version===1?completeDocument(editor.schema.nodeFromJSON(item.rich_content.document)):parseDocument(baselineMarkdown);if(editor.state.doc.eq(baselineDoc)){cachedDoc=editor.state.doc;markdownCache=baselineMarkdown;}},
  setValue(value){editor.commands.setContent(parseDocument(String(value||'')).toJSON());},
  insertMarkdown(value){editor.chain().focus().insertContent(String(value),{contentType:'markdown'}).run();},
  appendMarkdown(value){editor.chain().focus().insertContentAt(editor.state.doc.content.size,String(value),{contentType:'markdown'}).run();},
  insertText(value){editor.chain().focus().insertContent({type:'text',text:String(value)}).run();},
  selection(){const {from,to}=editor.state.selection;return {from,to,text:editor.state.doc.textBetween(from,to,' ')};},
  createBookmark,
  insertImage(attrs,reservation){const src=safeMedia(attrs.src);if(src)insertAtReservation({type:'image',attrs:{...attrs,src}},reservation);},
  insertPDF(attrs,reservation){const src=safeMedia(attrs.src);if(src)insertAtReservation({type:'pdf',attrs:{...attrs,src}},reservation);},
  insertReference(item){editor.chain().focus().insertContent({type:'documentLink',attrs:{id:Number(item.id),title:item.title}}).run();},
  insertPDFQuote({text,source,page,endPage=page,title='PDF 原文'}){
   const citation=pdfCitation(source+'#page='+page);if(!citation||typeof text!=='string'||!text.trim()||text.length>12000||editor.view.composing)return false;
   const pages=endPage>page?page+'–'+endPage:String(page);
   const nodes=[{type:'blockquote',content:text.trim().split(/\n+/).map(line=>({type:'paragraph',content:[{type:'text',text:line}]}))},{type:'paragraph',content:[{type:'text',text:title+' · 第 '+pages+' 页',marks:[{type:'link',attrs:{href:citation.src+'#page='+page,target:'_blank',rel:'noopener noreferrer nofollow'}}]}]},{type:'paragraph'}];
   editor.view.dispatch(closeHistory(editor.state.tr));
   // A source quote is inserted after the current block, never over selected notes.
   const {$to}=editor.state.selection,at=$to.depth?$to.after(1):$to.pos;
   const result=editor.chain().focus().insertContentAt(at,nodes).run();editor.view.dispatch(closeHistory(editor.state.tr));return result;
  },
  insertAttachment(file,reservation){insertAtReservation({type:'paragraph',content:[{type:'text',text:file.name,marks:[{type:'link',attrs:{href:'/files/'+file.id,target:'_blank',rel:'noopener noreferrer nofollow'}}]}]},reservation);},
  replacePDFSource(original,file){let tr=editor.state.tr;editor.state.doc.descendants((node,pos)=>{if(node.type.name==='pdf'&&new URL(node.attrs.src,location.origin).href===new URL(original,location.origin).href)tr=tr.setNodeMarkup(pos,undefined,{...node.attrs,src:'/files/'+file.id+'?inline=1',title:file.name||node.attrs.title});});if(tr.docChanged)editor.view.dispatch(tr);},
  setEditable(value){editor.setEditable(value,false);host.dataset.editable=String(value);if(!value)editor.view.dispatch(editor.state.tr.setMeta('bubbleMenu','hide'));hideSlash();blockMenu.hidden=true;codeBlocks.refresh();for(const checkbox of host.querySelectorAll('li[data-type="taskItem"] input'))checkbox.disabled=!value;},
  outline(){const headings=[];editor.state.doc.descendants((node,pos)=>{if(node.type.name==='heading')headings.push({level:node.attrs.level,title:node.textContent,pos});});return headings;},
  jump(pos){const node=editor.view.nodeDOM(pos);if(node instanceof HTMLElement)node.scrollIntoView({behavior:'smooth',block:'start'});if(editor.isEditable)editor.chain().focus().setTextSelection(Math.min(pos+1,editor.state.doc.content.size)).run();},
  active:isActive,command:run,
  heading:()=>editor.isActive('heading')?editor.getAttributes('heading').level:0,
  setHeading:level=>level?editor.chain().focus().setHeading({level:Number(level)}).run():editor.chain().focus().setParagraph().run(),
  tableFixedWidth:()=>selectedTable(editor)?.node.attrs.fixedWidth!==false,
  bodyFont,
  setBodyFont(value){if(!editor.isEditable||!['sans','serif','mono'].includes(value)||bodyFont()===value)return;editor.view.dispatch(closeHistory(editor.state.tr).step(new DocumentFontStep(value,bodyFont())));editor.view.dispatch(closeHistory(editor.state.tr));},
  setColor(color,{focus=true}={}){const chain=editor.chain();if(focus)chain.focus();return color?chain.setColor(color).run():chain.unsetColor().run();},
  focus:()=>editor.commands.focus(),undo:()=>editor.commands.undo(),redo:()=>editor.commands.redo(),
  showFind,measure:()=>{},
  destroy(){destroyed=true;cancelAnimationFrame(updateFrame);clearTimeout(blurTimer);clearTimeout(compositionTimer);cleanup.forEach(fn=>fn());reservations.clear();editor.destroy();owned.slice().forEach(el=>{if(el instanceof HTMLDialogElement&&el.open)el.close();el.remove();});host.replaceChildren();},
 };
 host.dataset.editable=String(editor.isEditable);scheduleControls();return adapter;
}
