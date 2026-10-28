import {Table,TableView} from '@tiptap/extension-table';
import {Plugin} from '@tiptap/pm/state';
import {TableMap,findTable,columnResizingPluginKey} from '@tiptap/pm/tables';
import {closeHistory} from '@tiptap/pm/history';

const views=new WeakMap();
const fixed=node=>node.attrs.fixedWidth!==false;
function weights(node){
 const map=TableMap.get(node);return Array.from({length:map.width},(_,col)=>{const pos=map.map[col],cell=node.nodeAt(pos);return cell.attrs.colwidth?.[col-map.colCount(pos)]||80;});
}
function storedWidths(widths,isFixed){
 const scale=isFixed?Math.max(1,25/Math.max(.1,Math.min(...widths))):1;
 return widths.map(value=>Math.max(isFixed?25:80,Math.min(5000,Math.round(value*scale))));
}
function writeWidths(tr,table,widths){
 const map=TableMap.get(table.node);
 for(const pos of new Set(map.map)){
  const cell=table.node.nodeAt(pos),col=map.colCount(pos),colwidth=widths.slice(col,col+cell.attrs.colspan);
  if(JSON.stringify(cell.attrs.colwidth)!==JSON.stringify(colwidth))tr.setNodeMarkup(table.start+pos,null,{...cell.attrs,colwidth});
 }
 return tr;
}
export function selectedTable(editor){
 const selection=editor.state.selection;
 return selection.node?.type.name==='table'?{node:selection.node,pos:selection.from,start:selection.from+1}:findTable(selection.$from);
}
class DocumentTableView extends TableView {
 constructor(node,minWidth,view,attributes){
  super(node,minWidth,view,attributes);views.set(this.dom,this);
  this.viewport=document.createElement('div');this.viewport.className='table-scroll-area';this.dom.insertBefore(this.viewport,this.table);this.viewport.append(this.table);
  this.scrollbar=document.createElement('input');this.scrollbar.type='range';this.scrollbar.className='table-horizontal-scroll';this.scrollbar.min='0';this.scrollbar.step='1';this.scrollbar.value='0';this.scrollbar.contentEditable='false';this.scrollbar.setAttribute('aria-label','表格横向滚动');this.scrollbar.title='横向滚动表格';this.scrollbar.hidden=true;this.dom.append(this.scrollbar);
  this.scrollbar.oninput=()=>{this.viewport.scrollLeft=Number(this.scrollbar.value);};this.onScroll=()=>this.syncScrollValue();this.viewport.addEventListener('scroll',this.onScroll,{passive:true});
  this.frame=0;this.destroyed=false;this.observer=new ResizeObserver(()=>this.scheduleScrollbar());this.observer.observe(this.viewport);this.observer.observe(this.table);this.paint();
 }
 syncScrollValue(){this.scrollbar.value=String(this.viewport.scrollLeft);this.scrollbar.setAttribute('aria-valuetext',Math.round(this.viewport.scrollLeft/Math.max(1,Number(this.scrollbar.max))*100)+'%');}
 scheduleScrollbar(){if(this.destroyed)return;if(!this.frame)this.frame=requestAnimationFrame(()=>{this.frame=0;if(this.destroyed)return;const max=Math.max(0,this.viewport.scrollWidth-this.viewport.clientWidth);this.scrollbar.max=String(max);this.scrollbar.hidden=fixed(this.node)||max<2;this.scrollbar.style.setProperty('--scroll-thumb-width',Math.max(24,this.viewport.clientWidth*this.viewport.clientWidth/Math.max(1,this.viewport.scrollWidth))+'px');this.syncScrollValue();});}

 paint(widths=weights(this.node)){
  const isFixed=fixed(this.node),total=widths.reduce((sum,value)=>sum+value,0);
  this.dom.dataset.fixedWidth=String(isFixed);this.table.dataset.fixedWidth=String(isFixed);this.dom.style.setProperty('--table-columns',String(widths.length));
  this.viewport.setAttribute('role','region');this.viewport.setAttribute('aria-label',isFixed?'固定宽度表格':'可横向滚动的表格');
  if(isFixed){this.viewport.removeAttribute('tabindex');this.viewport.scrollLeft=0;this.scrollbar.hidden=true;}else this.viewport.tabIndex=0;
  while(this.colgroup.children.length<widths.length)this.colgroup.append(document.createElement('col'));
  while(this.colgroup.children.length>widths.length)this.colgroup.lastChild.remove();
  Array.from(this.colgroup.children).forEach((col,index)=>{col.style.minWidth='0';col.style.width=isFixed?widths[index]/total*100+'%':widths[index]+'px';});
  this.table.style.width=isFixed?'100%':total+'px';this.table.style.minWidth='0';this.scheduleScrollbar();
 }
 update(node){if(node.type!==this.node.type)return false;this.node=node;this.paint();return true;}
 measuredWidths(){return Array.from(this.colgroup.children,col=>Math.max(.1,col.getBoundingClientRect().width));}
 stopEvent(event){return event.target===this.scrollbar;}
 destroy(){this.destroyed=true;this.observer.disconnect();cancelAnimationFrame(this.frame);this.viewport.removeEventListener('scroll',this.onScroll);this.scrollbar.oninput=null;views.delete(this.dom);}
}
function tableView(editor,table){return views.get(editor.view.nodeDOM(table.pos));}
function finishCommand(editor,tr){if(!tr.docChanged)return false;editor.view.dispatch(tr);editor.view.dispatch(closeHistory(editor.state.tr));return true;}
export function equalizeColumns(editor){
 const table=selectedTable(editor);if(!editor.isEditable||!table)return false;
 const renderer=tableView(editor,table),count=TableMap.get(table.node).width;if(!renderer||!count)return false;
 const width=renderer.table.getBoundingClientRect().width/count,values=storedWidths(Array(count).fill(width),fixed(table.node));
 return finishCommand(editor,writeWidths(closeHistory(editor.state.tr),table,values));
}
export function toggleTableWidth(editor){
 const table=selectedTable(editor);if(!editor.isEditable||!table)return false;
 const renderer=tableView(editor,table),isFixed=fixed(table.node);let tr=closeHistory(editor.state.tr);
 if(isFixed&&renderer)tr=writeWidths(tr,table,storedWidths(renderer.measuredWidths(),false));
 tr.setNodeMarkup(table.pos,null,{...table.node.attrs,fixedWidth:!isFixed});
 return finishCommand(editor,tr);
}
function boundedResizePlugin(base){
 let disposeDrag=null;
 const original=base.spec.props.handleDOMEvents;
 return new Plugin({...base.spec,props:{...base.spec.props,handleDOMEvents:{...original,
  mousemove(view,event){
   const result=original.mousemove(view,event),handle=columnResizingPluginKey.getState(view.state)?.activeHandle;
   if(view.editable&&handle>=0&&!columnResizingPluginKey.getState(view.state)?.dragging){
    const table=findTable(view.state.doc.resolve(handle));
    if(table&&fixed(table.node)){
     const map=TableMap.get(table.node),cell=view.state.doc.nodeAt(handle),col=map.colCount(handle-table.start)+cell.attrs.colspan-1;
     if(col===map.width-1)view.dispatch(view.state.tr.setMeta(columnResizingPluginKey,{setHandle:-1}));
    }
   }
   return result;
  },
  mousedown(view,event){
   if(!view.editable||event.button!==0)return false;
   const state=columnResizingPluginKey.getState(view.state);if(!state||state.activeHandle<0||state.dragging)return false;
   const table=findTable(view.state.doc.resolve(state.activeHandle)),renderer=table&&views.get(view.nodeDOM(table.pos));if(!renderer)return false;
   const map=TableMap.get(table.node),cell=view.state.doc.nodeAt(state.activeHandle),col=map.colCount(state.activeHandle-table.start)+cell.attrs.colspan-1,isFixed=fixed(table.node);
   if(isFixed&&col>=map.width-1)return false;
   const originalDoc=view.state.doc,startX=event.clientX,widths=renderer.measuredWidths(),total=widths.reduce((sum,width)=>sum+width,0),minimum=Math.min(40,total/widths.length/2),win=view.dom.ownerDocument.defaultView;
   let done=false;
   function resized(x){const next=widths.slice();let delta=x-startX;if(isFixed){delta=Math.max(minimum-widths[col],Math.min(widths[col+1]-minimum,delta));next[col]+=delta;next[col+1]-=delta;}else next[col]=Math.max(80,Math.min(5000,widths[col]+delta));return next;}
   function dispose(){win.removeEventListener('mousemove',move);win.removeEventListener('mouseup',finish);win.removeEventListener('blur',cancel);win.removeEventListener('keydown',escape,true);disposeDrag=null;}
   function end(commit,event){
    if(done)return;done=true;dispose();const unchanged=view.state.doc===originalDoc&&view.editable;
    if(commit&&unchanged&&Math.abs(event.clientX-startX)>=1){const tr=writeWidths(closeHistory(view.state.tr),table,storedWidths(resized(event.clientX),isFixed));tr.setMeta(columnResizingPluginKey,{setHandle:-1});view.dispatch(tr);view.dispatch(closeHistory(view.state.tr));}
    else{renderer.paint();if(!view.isDestroyed)view.dispatch(view.state.tr.setMeta(columnResizingPluginKey,{setHandle:-1}));}
   }
   function move(event){if(!event.buttons||view.state.doc!==originalDoc||!view.editable)return end(false,event);renderer.paint(resized(event.clientX));}
   function finish(event){end(true,event);}
   function cancel(event){end(false,event);}
   function escape(event){if(event.key==='Escape'){event.preventDefault();event.stopPropagation();end(false,event);}}
   view.dispatch(closeHistory(view.state.tr).setMeta(columnResizingPluginKey,{setDragging:{startX,startWidth:widths[col]}}));
   disposeDrag=()=>{done=true;dispose();};win.addEventListener('mousemove',move);win.addEventListener('mouseup',finish);win.addEventListener('blur',cancel);win.addEventListener('keydown',escape,true);event.preventDefault();return true;
  }
 }},view(){return {destroy(){disposeDrag?.();}};}});
}
export const DocumentTable=Table.extend({
 addAttributes(){return {...this.parent?.(),fixedWidth:{default:true,parseHTML:element=>element.getAttribute('data-fixed-width')!=='false',renderHTML:attrs=>({'data-fixed-width':String(attrs.fixedWidth!==false)})}};},
 addProseMirrorPlugins(){return (this.parent?.()||[]).map(plugin=>plugin.spec.key===columnResizingPluginKey?boundedResizePlugin(plugin):plugin);},
}).configure({resizable:true,cellMinWidth:80,allowTableNodeSelection:true,View:DocumentTableView});
