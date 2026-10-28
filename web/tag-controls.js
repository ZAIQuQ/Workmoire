import {PAPER_TAG,tagName as nameOf,tagKey as key,tagColor,documentTags} from './tag-colors.js';
export {tagColor,documentTags} from './tag-colors.js';
const icon=name=>window.WorkmoireIcons.render(name);
const button=(text,cls)=>{const el=document.createElement('button');el.type='button';el.className=cls;el.textContent=text;return el;};
const badge=tag=>{const el=document.createElement('span');el.className='bookmark-tag';el.dataset.tagColor=tagColor(tag);el.textContent=tag;return el;};
let nextId=0;

// Shared management view, embedded in the row entry and in the full tag library.
function mountTagManager(host,{request,post,onSelect,onExecute,onBusy=()=>{},onLayout=()=>{},kind='',embedded=false}){
 let version=0,timer,disposed=false,busy=false,rows=[],next=null,actionVersion=0,actionTimer;
 const catalog=document.createElement('div');catalog.className='tag-management-catalog';
 catalog.innerHTML='<div class="tag-library-search">'+icon('search')+'<input type="search" aria-label="搜索所有标签" placeholder="搜索所有标签" autocomplete="off"></div><div class="tag-library-shortcuts"></div><div class="tag-library-caption"><span>全部标签</span><span>文档数</span></div><div class="tag-library-rows"></div><div class="tag-library-pages"></div><div class="tag-library-status" role="status"></div>';
 const actionHost=document.createElement('div');actionHost.hidden=true;host.append(catalog,actionHost);
 const input=catalog.querySelector('input'),root=catalog.querySelector('.tag-library-rows'),pages=catalog.querySelector('.tag-library-pages'),status=catalog.querySelector('.tag-library-status');
 async function load(append=false){
  const mine=++version;status.textContent='正在加载…';
  try{
   const data=await request('/api/tags?'+new URLSearchParams({q:input.value,limit:'30',offset:append?String(next):'0',kind}));if(disposed||mine!==version)return;
   rows=append?rows.concat(data.tags):data.tags;next=data.next_offset;root.replaceChildren();pages.replaceChildren();status.textContent=rows.length?'':'还没有匹配的标签';
   catalog.querySelector('.tag-library-caption span').textContent='全部标签 · '+data.total;
   const shortcuts=catalog.querySelector('.tag-library-shortcuts');shortcuts.replaceChildren();shortcuts.hidden=embedded;
   if(!embedded)for(const [label,tag,empty] of [[kind?'全部论文':'全部文档','',false],['无标签 · '+data.untagged,'',true]]){const el=button(label,'tag-library-shortcut');el.onclick=()=>onSelect(tag,empty);shortcuts.append(el);}
   for(const item of rows){
    const row=document.createElement('div');row.className='tag-library-row';const pick=button('','tag-library-pick');pick.innerHTML=icon('bookmark');pick.append(badge(item.tag));pick.title=embedded?'添加到当前文档':'筛选这个标签';pick.onclick=()=>onSelect(item.tag);
    const count=document.createElement('span');count.className='tag-use-count';count.textContent=item.count;row.append(pick,count);
    if(item.built_in||item.tag===PAPER_TAG){const lock=document.createElement('span');lock.className='tag-library-lock';lock.innerHTML=icon('lock');lock.title='内置标签不能删除或重命名';const note=document.createElement('span');note.className='tag-system-badge';note.textContent='内置';row.append(note,lock);}
    else{const rename=button('改名','tag-library-edit'),remove=button('删除','tag-library-delete');rename.setAttribute('aria-label','改名标签 '+item.tag);remove.setAttribute('aria-label','删除标签 '+item.tag);rename.onclick=()=>editTag(item,'rename');remove.onclick=()=>editTag(item,'delete');row.append(rename,remove);}
    root.append(row);
   }
   if(next!==null){const more=button('加载更多','quiet-button');more.onclick=()=>load(true);pages.append(more);}onLayout();
  }catch(error){if(mine===version&&!disposed)status.textContent=error.message;}
 }
 function back(){actionVersion++;clearTimeout(actionTimer);actionHost.replaceChildren();actionHost.hidden=true;catalog.hidden=false;input.focus();onLayout();}
 function editTag(item,action){
  if(busy||item.built_in||item.tag===PAPER_TAG)return;
  catalog.hidden=true;actionHost.hidden=false;actionHost.replaceChildren();
  const form=document.createElement('form');form.className='tag-rename-form';
  form.innerHTML='<button type="button" class="quiet-button tag-rename-back">'+icon('back')+'返回标签列表</button><h3></h3><p class="tag-rename-source"></p><div class="tag-target-field"></div><div class="tag-rename-preview" role="status"></div><div class="dialog-actions"><button type="submit" class="button primary" disabled>加载预览…</button></div>';
  form.querySelector('h3').textContent=action==='delete'?'删除标签':'重命名标签';form.querySelector('.tag-rename-source').textContent='标签：'+item.tag;
  let field=null,plan=null;
  if(action==='rename'){const label=document.createElement('label');label.className='field';const text=document.createElement('span');text.textContent='新的标签名称';field=document.createElement('input');field.setAttribute('aria-label','新的标签名称');field.maxLength=32;field.required=true;field.value=item.tag;label.append(text,field);form.querySelector('.tag-target-field').append(label);}
  const preview=form.querySelector('.tag-rename-preview'),submit=form.querySelector('[type="submit"]'),backButton=form.querySelector('.tag-rename-back');backButton.onclick=back;
  async function previewChange(){
   const mine=++actionVersion;plan=null;submit.disabled=true;submit.textContent='加载预览…';
   if(field&&(!nameOf(field.value)||nameOf(field.value)===item.tag)){preview.textContent='输入新名称；已有名称会合并为同一个标签。';submit.textContent='确认改名';return;}
   try{const result=await post('/api/tags/preview',{source:item.tag,target:field?.value,action});if(disposed||mine!==actionVersion||!form.isConnected)return;plan=result;preview.replaceChildren();const summary=document.createElement('p');summary.textContent=action==='delete'?'将从 '+plan.count+' 份文档中删除「'+item.tag+'」标签，文档内容保留。':(plan.merge?'合并到':'重命名为')+'「'+plan.target+'」，影响整个空间中的 '+plan.count+' 份文档。';preview.append(summary);const list=document.createElement('ul');for(const doc of plan.items){const li=document.createElement('li');li.textContent=doc.title;list.append(li);}preview.append(list);const note=document.createElement('p');note.className='quiet';note.textContent='可在各文档的历史版本中恢复。';preview.append(note);submit.textContent=action==='delete'?'确认删除标签':plan.merge?'确认合并':'确认改名';submit.classList.toggle('tag-delete-confirm',action==='delete');submit.disabled=false;onLayout();}catch(error){if(mine===actionVersion&&!disposed){preview.textContent=error.message;submit.textContent='重新预览';submit.disabled=false;}}
  }
  if(field)field.oninput=()=>{actionVersion++;plan=null;submit.disabled=true;clearTimeout(actionTimer);actionTimer=setTimeout(previewChange,150);};
  form.onsubmit=async event=>{
   event.preventDefault();if(busy)return;if(!plan){await previewChange();return;}busy=true;onBusy(true);submit.disabled=true;backButton.disabled=true;if(field)field.disabled=true;
   try{const result=await onExecute(plan);if(disposed)return;back();input.value=result.action==='delete'?'':result.target;await load();status.textContent=result.action==='delete'?'标签已从 '+result.count+' 份文档中删除':'已'+(result.merge?'合并':'改名')+'，更新 '+result.count+' 份文档';}
   catch(error){if(!disposed){preview.textContent=error.message;plan=null;submit.textContent='重新预览';submit.disabled=false;}}
   finally{busy=false;onBusy(false);backButton.disabled=false;if(field)field.disabled=false;onLayout();}
  };
  actionHost.append(form);previewChange();if(field){field.focus();field.select();}else backButton.focus();onLayout();
 }
 input.oninput=()=>{clearTimeout(timer);version++;timer=setTimeout(()=>load(),150);};
 return {load,back,destroy(){disposed=true;version++;actionVersion++;clearTimeout(timer);clearTimeout(actionTimer);},isBusy:()=>busy};
}

export function openDocumentTagPicker({anchor,item,request,post,onApply,onExecute,onClose}){
 item={...item};let current=documentTags(item.tags,item.kind),known=[],choices=[],active=0,selectedByArrow=false,version=0,timer,closed=false,busy=false,composing=false;
 const isNew=!item.id,dialog=document.createElement('dialog');dialog.className='dialog row-tag-dialog';dialog.setAttribute('aria-label','管理文档标签');
 const header=document.createElement('header');header.className='row-tag-header';const heading=document.createElement('strong');heading.textContent='文档标签';const title=document.createElement('span');title.textContent=item.title||'未命名文档';header.append(heading,title);
 const tabs=document.createElement('div');tabs.className='row-tag-tabs';tabs.setAttribute('role','tablist');const docTab=button('文档标签','row-tag-tab'),manageTab=button('管理标签','row-tag-tab');tabs.append(docTab,manageTab);
 const docPanel=document.createElement('div');docPanel.className='row-tag-body';docPanel.id='document-labels-'+(++nextId);docPanel.setAttribute('role','tabpanel');
 const managerHost=document.createElement('div');managerHost.className='row-tag-manager';managerHost.id='manage-labels-'+nextId;managerHost.setAttribute('role','tabpanel');managerHost.hidden=true;
 for(const [tab,panel] of [[docTab,docPanel],[manageTab,managerHost]]){tab.setAttribute('role','tab');tab.setAttribute('aria-controls',panel.id);}
 const createButton=button('新建标签','button secondary small tag-create-trigger');createButton.innerHTML=icon('plus')+'新建标签';
 const form=document.createElement('form');form.className='tag-create-form';form.hidden=true;form.innerHTML='<label class="field"><span>新标签名称</span><input aria-label="新标签名称" maxlength="32" placeholder="例如：实验记录" autocomplete="off" required></label><div class="tag-create-actions"><button type="button" class="quiet-button tag-create-cancel">取消</button><button type="submit" class="button primary small">创建并添加</button></div>';
 const newName=form.querySelector('input');form.querySelector('.tag-create-cancel').onclick=()=>{form.hidden=true;position();createButton.focus();};
 const selectedTitle=document.createElement('div');selectedTitle.className='tag-picker-caption';selectedTitle.textContent='当前文档';const selected=document.createElement('div');selected.className='tag-picker-selected';
 const input=document.createElement('input');input.placeholder='搜索已有标签，或输入名称按 Enter 新建';input.setAttribute('aria-label','搜索或创建标签');input.setAttribute('role','combobox');input.setAttribute('aria-autocomplete','list');input.setAttribute('aria-expanded','true');input.autocomplete='off';
 const caption=document.createElement('div');caption.className='tag-picker-caption';const list=document.createElement('div');list.className='tag-options';list.id='tag-options-'+nextId;list.setAttribute('role','listbox');input.setAttribute('aria-controls',list.id);
 const status=document.createElement('div');status.className='tag-picker-status';status.setAttribute('role','status');
 const footer=document.createElement('footer');footer.className='row-tag-footer';const hint=document.createElement('span');hint.textContent=isNew?'新文档的标签随文档保存':'添加和移除会立即保存';const done=button('完成','button secondary small');footer.append(hint,done);
 docPanel.append(createButton,form,selectedTitle,selected,input,caption,list,status);dialog.append(header,tabs,docPanel,managerHost,footer);document.body.append(dialog);
 let anchorBox=anchor?.getBoundingClientRect()||{right:24,top:80};
 function position(){if(!dialog.open)return;const width=dialog.offsetWidth,height=dialog.offsetHeight,left=innerWidth<=760?(innerWidth-width)/2:Math.min(anchorBox.right+8,innerWidth-width-12);dialog.style.left=Math.max(12,left)+'px';dialog.style.top=Math.max(12,Math.min(anchorBox.top-8,innerHeight-height-12))+'px';}
 function setBusy(value){busy=value;docTab.disabled=value;manageTab.disabled=value;done.disabled=value;docPanel.inert=value;createButton.disabled=value;input.disabled=value;}
 function renderSelected(){
  selected.replaceChildren();selectedTitle.hidden=!current.length;
  for(const tag of current){const chip=badge(tag);chip.classList.add('selected-tag');const text=document.createElement('span');text.textContent=tag;chip.replaceChildren(text);
   if(item.kind==='paper'&&tag===PAPER_TAG){const lock=document.createElement('span');lock.className='tag-lock';lock.innerHTML=icon('lock');lock.title='论文档案的内置标签，不能移除';lock.setAttribute('aria-label',lock.title);chip.append(lock);}
   else{const remove=button('','tag-remove');remove.innerHTML=icon('close');remove.title='从此文档移除';remove.setAttribute('aria-label','从此文档移除标签 '+tag);remove.onclick=()=>change(current.filter(t=>t!==tag),'已从此文档移除');chip.append(remove);}selected.append(chip);
  }
  selected.hidden=!current.length;position();
 }
 async function change(next,message){
  if(busy)return false;version++;setBusy(true);status.textContent=isNew?'正在更新草稿…':'正在保存…';
  try{const result=await onApply(next.join(','),item);if(result)Object.assign(item,result);current=documentTags(result?.tags??next.join(','),item.kind);renderSelected();status.textContent=isNew?'已加入本机草稿':message;return true;}
  catch(error){status.textContent=error.message;return false;}
  finally{setBusy(false);load();}
 }
 async function add(raw){
  if(busy)return false;const names=String(raw).replaceAll('，',',').split(',').map(nameOf).filter(Boolean);if(!names.length){status.textContent='请输入标签名称';return false;}if(names.some(name=>Array.from(name).length>32)){status.textContent='标签名称最多 32 个字符';return false;}
  // Explicit creation/Enter works even while debounced suggestions are pending.
  version++;setBusy(true);status.textContent='正在添加标签…';let next=[...current];
  try{for(const name of names){const result=await request('/api/tags?'+new URLSearchParams({limit:'100',q:name}));const tag=result.tags.find(option=>key(option.tag)===key(name))?.tag||name;if(!next.some(value=>key(value)===key(tag)))next.push(tag);}
   if(next.filter(tag=>item.kind!=='paper'||tag!==PAPER_TAG).length>12)throw new Error('每份文档最多 12 个自定义标签');
  }catch(error){setBusy(false);status.textContent=error.message;return false;}
  setBusy(false);if(next.join(',')===current.join(',')){status.textContent='此文档已添加这个标签';return true;}
  const ok=await change(documentTags(next.join(','),item.kind),'已添加并保存');if(ok){input.value='';form.hidden=true;renderSelected();load();input.focus();}return ok;
 }
 function paint(){list.replaceChildren();input.removeAttribute('aria-activedescendant');choices.forEach((choice,index)=>{const row=button('','tag-option');row.id=list.id+'-'+index;row.setAttribute('role','option');row.setAttribute('aria-selected',String(index===active));row.innerHTML=icon(choice.create?'plus':'bookmark');const label=badge(choice.tag);label.classList.add('tag-option-label');label.textContent=choice.create?'创建「'+choice.tag+'」并添加':choice.tag;const detail=document.createElement('small');detail.textContent=choice.create?'Enter':choice.built_in?'内置':choice.title_match?'标题匹配':choice.related?'常一起使用':choice.count+' 份';row.append(label,detail);row.onmousedown=event=>event.preventDefault();row.onclick=()=>add(choice.tag);list.append(row);});if(choices.length&&active>=0)input.setAttribute('aria-activedescendant',list.id+'-'+active);position();}
 async function load(){
  const mine=++version,query=nameOf(input.value);choices=[];paint();caption.textContent=query?'匹配的标签':'建议标签';
  try{const result=await request('/api/tags?'+new URLSearchParams({limit:'20',q:query,title:String(item.title||'').slice(0,200),context:current.at(-1)||''}));if(closed||mine!==version)return;known=result.tags;choices=known.filter(option=>!current.some(tag=>key(tag)===key(option.tag)));if(query&&!/[,，]/.test(query)&&Array.from(query).length<=32&&!known.some(option=>key(option.tag)===key(query))&&!current.some(tag=>key(tag)===key(query)))choices.push({tag:query,create:true});active=current.some(tag=>key(tag)===key(query))?-1:Math.max(0,choices.findIndex(option=>option.create||key(option.tag)===key(query)));selectedByArrow=false;paint();}
  catch(error){if(!closed&&mine===version)status.textContent=error.message;}
 }
 function show(mode){hint.textContent=mode==='manage'?'改名和删除会先预览影响范围':isNew?'新文档的标签随文档保存':'添加和移除会立即保存';docPanel.hidden=mode!=='document';managerHost.hidden=mode!=='manage';docTab.setAttribute('aria-selected',String(mode==='document'));manageTab.setAttribute('aria-selected',String(mode==='manage'));if(mode==='manage')manager.load();else load();position();}
 const manager=mountTagManager(managerHost,{request,post,embedded:true,onBusy:setBusy,onLayout:position,onSelect:async tag=>{show('document');await add(tag);},onExecute:async plan=>{
  const result=await onExecute(plan);const update=result.updates?.find(update=>update.before.id===item.id);
  if(update&&update.before.updated_at===item.updated_at){Object.assign(item,update.after);current=documentTags(item.tags,item.kind);}
  else if(isNew){const next=current.flatMap(tag=>tag!==result.source?[tag]:result.action==='delete'?[]:[result.target]);const unique=[...new Set(next)];const saved=await onApply(documentTags(unique.join(','),item.kind).join(','),item);if(saved)Object.assign(item,saved);current=documentTags(saved?.tags??unique.join(','),item.kind);}
  renderSelected();return result;
 }});
 createButton.onclick=()=>{form.hidden=false;newName.value=input.value;position();newName.focus();};
 newName.oncompositionstart=()=>composing=true;newName.oncompositionend=()=>composing=false;newName.onkeydown=event=>{if(event.key==='Enter'&&(event.isComposing||composing))event.preventDefault();};form.onsubmit=async event=>{event.preventDefault();if(!composing)await add(newName.value);};
 input.oninput=event=>{clearTimeout(timer);version++;choices=[];selectedByArrow=false;paint();if(!event.isComposing)timer=setTimeout(load,120);};
 input.onkeydown=event=>{if(event.isComposing||busy)return;if(['ArrowDown','ArrowUp'].includes(event.key)&&choices.length){event.preventDefault();selectedByArrow=true;active=active<0?(event.key==='ArrowDown'?0:choices.length-1):(active+(event.key==='ArrowDown'?1:-1)+choices.length)%choices.length;paint();list.children[active]?.scrollIntoView({block:'nearest'});}if(event.key==='Enter'){event.preventDefault();add(selectedByArrow&&choices[active]?choices[active].tag:input.value||choices[active]?.tag||'');}};
 docTab.onclick=()=>show('document');manageTab.onclick=()=>show('manage');done.onclick=()=>dialog.close();
 dialog.addEventListener('cancel',event=>{if(busy)event.preventDefault();});dialog.addEventListener('close',()=>{closed=true;version++;clearTimeout(timer);manager.destroy();window.removeEventListener('resize',position);dialog.remove();onClose?.();});dialog.addEventListener('click',event=>{if(event.target===dialog&&!busy){const r=dialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)dialog.close();}});
 window.addEventListener('resize',position);dialog.showModal();show('document');renderSelected();input.focus();return dialog;
}

export function openTagLibrary({request,post,onSelect,onExecute,kind=''}){
 const dialog=document.createElement('dialog');dialog.className='dialog tag-library-dialog';dialog.setAttribute('aria-label','标签管理');
 const card=document.createElement('div');card.className='dialog-card tag-library';card.innerHTML='<div class="dialog-head"><h2></h2><button type="button" class="icon-button tag-library-close" aria-label="关闭标签">'+icon('close')+'</button></div>';
 card.querySelector('h2').textContent=kind?'论文标签':'标签';const host=document.createElement('div');card.append(host);dialog.append(card);document.body.append(dialog);let busy=false;
 const close=card.querySelector('.tag-library-close');const manager=mountTagManager(host,{request,post,kind,onExecute,onBusy:value=>{busy=value;close.disabled=value;},onSelect:(tag,empty)=>{onSelect(tag,empty);dialog.close();}});
 close.onclick=()=>dialog.close();dialog.addEventListener('cancel',event=>{if(busy)event.preventDefault();});dialog.addEventListener('close',()=>{manager.destroy();dialog.remove();});dialog.addEventListener('click',event=>{if(event.target===dialog&&!busy){const r=dialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)dialog.close();}});dialog.showModal();manager.load();host.querySelector('input').focus();return dialog;
}
