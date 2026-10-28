import {PAPER_TAG,tagName as nameOf,tagKey as key,tagColor,documentTags} from './tag-colors.js';
export {tagColor,documentTags} from './tag-colors.js';
const icon=name=>window.WorkmoireIcons.render(name);
const button=(text,cls)=>{const el=document.createElement('button');el.type='button';el.className=cls;el.textContent=text;return el;};
let nextId=0;

export function openDocumentTagPicker({anchor,item,request,onApply,onClose}){
 let current=documentTags(item.tags,item.kind),known=[],choices=[],active=0,version=0,timer,closed=false,busy=false;
 const initial=current.join(','),isNew=!item.id;
 const dialog=document.createElement('dialog');dialog.className='dialog row-tag-dialog';dialog.setAttribute('aria-label','管理文档标签');
 const header=document.createElement('header');header.className='row-tag-header';const heading=document.createElement('strong');heading.textContent='文档标签';const title=document.createElement('span');title.textContent=item.title||'未命名文档';header.append(heading,title);
 const input=document.createElement('input');input.placeholder='搜索或创建标签';input.setAttribute('aria-label','搜索或创建标签');input.setAttribute('role','combobox');input.setAttribute('aria-autocomplete','list');input.setAttribute('aria-expanded','true');input.autocomplete='off';
 const selected=document.createElement('div');selected.className='tag-picker-selected';
 const caption=document.createElement('div');caption.className='tag-picker-caption';
 const list=document.createElement('div');list.className='tag-options';list.id='tag-options-'+(++nextId);list.setAttribute('role','listbox');input.setAttribute('aria-controls',list.id);
 const status=document.createElement('div');status.className='tag-picker-status';status.setAttribute('role','status');
 const footer=document.createElement('footer');footer.className='row-tag-footer';const cancel=button('取消','button secondary small'),apply=button(isNew?'应用到草稿':'保存标签','button primary small');footer.append(cancel,apply);
 const body=document.createElement('div');body.className='row-tag-body';body.append(input,selected,caption,list,status);dialog.append(header,body,footer);document.body.append(dialog);
 function renderSelected(){
  selected.replaceChildren();for(const tag of current){
   const chip=document.createElement('span');chip.className='selected-tag bookmark-tag';chip.dataset.tagColor=tagColor(tag);const text=document.createElement('span');text.textContent=tag;chip.append(text);
   if(item.kind==='paper'&&tag===PAPER_TAG){const lock=document.createElement('span');lock.className='tag-lock';lock.innerHTML=icon('lock');lock.title='论文档案的内置标签，不能移除';lock.setAttribute('aria-label',lock.title);chip.append(lock);}
   else{const remove=button('','tag-remove');remove.innerHTML=icon('close');remove.setAttribute('aria-label','移除标签 '+tag);remove.onclick=()=>{current=current.filter(t=>t!==tag);changed();};chip.append(remove);}
   selected.append(chip);
  }
  selected.hidden=!current.length;apply.disabled=busy||current.join(',')===initial;position();
 }
 function changed(){renderSelected();input.focus();load();}
 function add(raw){
  const next=[...current];for(let tag of String(raw).replaceAll('，',',').split(',').map(nameOf).filter(Boolean)){
   if(Array.from(tag).length>32){status.textContent='标签名称最多 32 个字符';return;}
   tag=known.find(candidate=>key(candidate.tag)===key(tag))?.tag||tag;if(!next.some(value=>key(value)===key(tag)))next.push(tag);
  }
  if(next.filter(tag=>item.kind!=='paper'||tag!==PAPER_TAG).length>12){status.textContent='每份文档最多 12 个自定义标签';return;}
  current=documentTags(next.join(','),item.kind);input.value='';changed();
 }
 function paint(){
  list.replaceChildren();input.removeAttribute('aria-activedescendant');
  choices.forEach((choice,index)=>{const row=button('','tag-option');row.id=list.id+'-'+index;row.setAttribute('role','option');row.setAttribute('aria-selected',String(index===active));row.innerHTML=icon(choice.create?'plus':'bookmark');const label=document.createElement('span');label.className='tag-option-label bookmark-tag';label.dataset.tagColor=tagColor(choice.tag);label.textContent=choice.create?'创建「'+choice.tag+'」':choice.tag;const detail=document.createElement('small');detail.textContent=choice.create?'Enter':choice.built_in?'内置':choice.title_match?'标题匹配':choice.related?'常一起使用':choice.count+' 份';row.append(label,detail);row.onmousedown=event=>event.preventDefault();row.onclick=()=>add(choice.tag);list.append(row);});
  if(choices.length)input.setAttribute('aria-activedescendant',list.id+'-'+active);position();
 }
 async function load(){
  const mine=++version,query=nameOf(input.value);choices=[];paint();status.textContent='';caption.textContent=query?'匹配的标签':'建议标签';
  try{const result=await request('/api/tags?'+new URLSearchParams({limit:'20',q:query,title:String(item.title||'').slice(0,200),context:current.at(-1)||''}));if(closed||mine!==version)return;
   known=result.tags;choices=known.filter(option=>!current.some(tag=>key(tag)===key(option.tag)));
   if(query&&!/[,，]/.test(query)&&Array.from(query).length<=32&&!known.some(option=>key(option.tag)===key(query))&&!current.some(tag=>key(tag)===key(query)))choices.push({tag:query,create:true});
   active=0;paint();if(!choices.length)status.textContent=/[,，]/.test(query)?'按 Enter 添加这些标签':query?'没有其他匹配标签':'输入名称创建标签';
  }catch(error){if(mine===version&&!closed){status.textContent=error.message;}}
 }
 function position(){
  if(!dialog.open)return;
  const rect=anchor?.isConnected?anchor.getBoundingClientRect():{left:12,right:24,top:80},width=dialog.offsetWidth,height=dialog.offsetHeight;
  const left=innerWidth<=760?(innerWidth-width)/2:Math.min(rect.right+8,innerWidth-width-12);
  dialog.style.left=Math.max(12,left)+'px';dialog.style.top=Math.max(12,Math.min(rect.top-8,innerHeight-height-12))+'px';
 }
 input.oninput=event=>{clearTimeout(timer);version++;choices=[];paint();if(!event.isComposing)timer=setTimeout(load,120);};
 input.onkeydown=event=>{if(event.isComposing)return;if(['ArrowDown','ArrowUp'].includes(event.key)&&choices.length){event.preventDefault();active=(active+(event.key==='ArrowDown'?1:-1)+choices.length)%choices.length;paint();list.children[active]?.scrollIntoView({block:'nearest'});}if(event.key==='Enter'){event.preventDefault();if(/[,，]/.test(input.value))add(input.value);else if(choices[active])add(choices[active].tag);}};
 cancel.onclick=()=>dialog.close();
 apply.onclick=async()=>{if(busy||apply.disabled)return;busy=true;apply.disabled=true;cancel.disabled=true;input.disabled=true;selected.querySelectorAll('button').forEach(el=>el.disabled=true);list.inert=true;status.textContent=isNew?'正在更新草稿…':'正在保存标签…';try{await onApply(current.join(','));dialog.close();}catch(error){status.textContent=error.message;}finally{busy=false;cancel.disabled=false;input.disabled=false;list.inert=false;renderSelected();}};
 dialog.addEventListener('cancel',event=>{if(busy)event.preventDefault();});dialog.addEventListener('close',()=>{closed=true;version++;clearTimeout(timer);window.removeEventListener('resize',position);dialog.remove();onClose?.();});
 dialog.addEventListener('click',event=>{if(event.target===dialog&&!busy){const r=dialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)dialog.close();}});
 window.addEventListener('resize',position);dialog.showModal();renderSelected();input.focus();load();return dialog;
}

export function openTagLibrary({request,post,onSelect,onApplied,beforeApply,kind=''}){
 const dialog=document.createElement('dialog');dialog.className='dialog tag-library-dialog';
 const card=document.createElement('div');card.className='dialog-card tag-library';dialog.setAttribute('aria-label','标签管理');
 card.innerHTML='<div class="dialog-head"><h2>标签</h2><button type="button" class="icon-button tag-library-close" aria-label="关闭标签">'+icon('close')+'</button></div><div class="tag-library-search">'+icon('search')+'<input type="search" aria-label="搜索所有标签" placeholder="搜索标签" autocomplete="off"></div><div class="tag-library-shortcuts"></div><div class="tag-library-caption"><span>全部标签</span><span>文档数</span></div><div class="tag-library-rows"></div><div class="tag-library-pages"></div><div class="tag-library-status" role="status"></div>';
 card.querySelector('h2').textContent=kind?'论文标签':'标签';dialog.append(card);document.body.append(dialog);let version=0,timer,rows=[],next=null,disposed=false,busy=false;
 const input=card.querySelector('input'),root=card.querySelector('.tag-library-rows'),pages=card.querySelector('.tag-library-pages'),status=card.querySelector('.tag-library-status');
 card.querySelector('.tag-library-close').onclick=()=>dialog.close();
 const choose=(tag,untagged=false)=>{onSelect(tag,untagged);dialog.close();};
 async function load(append=false){
  const mine=++version;status.textContent='正在加载…';
  try{
   const data=await request('/api/tags?'+new URLSearchParams({q:input.value,limit:'30',offset:append?String(next):'0',kind}));if(disposed||mine!==version)return;
   rows=append?rows.concat(data.tags):data.tags;next=data.next_offset;root.replaceChildren();pages.replaceChildren();status.textContent=rows.length?'':'还没有匹配的标签';
   card.querySelector('.tag-library-caption span').textContent='全部标签 · '+data.total;
   const shortcuts=card.querySelector('.tag-library-shortcuts');shortcuts.replaceChildren();for(const [label,tag,empty] of [[kind?'全部论文':'全部文档','',false],['无标签 · '+data.untagged,'',true]]){const el=button(label,'tag-library-shortcut');el.onclick=()=>choose(tag,empty);shortcuts.append(el);}
   for(const item of rows){
    const row=document.createElement('div');row.className='tag-library-row';const pick=button('','tag-library-pick');pick.innerHTML=icon('bookmark');const label=document.createElement('span');label.className='bookmark-tag';label.dataset.tagColor=tagColor(item.tag);label.textContent=item.tag;pick.append(label);pick.onclick=()=>choose(item.tag);
    const count=document.createElement('span');count.className='tag-use-count';count.textContent=item.count;
    const edit=button('','tag-library-edit');edit.innerHTML=icon('write');edit.title='重命名或合并';edit.setAttribute('aria-label','整理标签 '+item.tag);edit.onclick=()=>editTag(item);row.append(pick);if(item.built_in||item.tag===PAPER_TAG){const badge=document.createElement('span');badge.className='tag-system-badge';badge.textContent='内置';const lock=document.createElement('span');lock.className='tag-library-lock';lock.innerHTML=icon('lock');lock.title='内置标签不能删除或重命名';row.append(badge,count,lock);}else row.append(count,edit);root.append(row);
   }
   if(next!==null){const more=button('加载更多','quiet-button');more.onclick=()=>load(true);pages.append(more);}
  }catch(error){if(mine===version)status.textContent=error.message;}
 }
 function editTag(item){
  if(busy||item.built_in||item.tag===PAPER_TAG)return;
  const form=document.createElement('form');form.className='tag-rename-form';form.innerHTML='<button type="button" class="quiet-button tag-rename-back">'+icon('back')+'全部标签</button><h3>重命名或合并</h3><p class="tag-rename-source"></p><label class="field"><span>新的标签名称</span><input aria-label="新的标签名称" maxlength="32" autocomplete="off" required></label><div class="tag-rename-preview" role="status"></div><div class="dialog-actions"><button type="submit" class="button primary" disabled>预览修改</button></div>';
  card.hidden=true;dialog.append(form);const field=form.querySelector('input'),preview=form.querySelector('.tag-rename-preview'),submit=form.querySelector('[type="submit"]');field.value=item.tag;form.querySelector('.tag-rename-source').textContent='当前标签：'+item.tag;
  let plan=null,revision=0,previewTimer;
  const back=()=>{revision++;clearTimeout(previewTimer);form.remove();card.hidden=false;input.focus();};form.querySelector('.tag-rename-back').onclick=back;
  const update=async()=>{const mine=++revision;plan=null;submit.disabled=true;submit.textContent='预览修改';if(nameOf(field.value)===item.tag||!nameOf(field.value)){preview.textContent='输入新名称；已有名称会合并为同一个标签。';return;}try{
   const result=await post('/api/tags/preview',{source:item.tag,target:field.value});if(disposed||mine!==revision||!form.isConnected)return;plan=result;preview.replaceChildren();const summary=document.createElement('p');summary.textContent=(plan.merge?'合并到':'重命名为')+'「'+plan.target+'」，影响整个空间中的 '+plan.count+' 份文档。';preview.append(summary);
   const titles=document.createElement('ul');plan.items.forEach(item=>{const li=document.createElement('li');li.textContent=item.title;titles.append(li);});preview.append(titles);const note=document.createElement('p');note.className='quiet';note.textContent='每份文档会保留修改前的历史版本。';preview.append(note);submit.textContent=plan.merge?'确认合并':'确认重命名';submit.disabled=false;
  }catch(error){if(mine===revision)preview.textContent=error.message;}};
  field.oninput=()=>{revision++;plan=null;submit.disabled=true;clearTimeout(previewTimer);previewTimer=setTimeout(update,180);};
  form.onsubmit=async event=>{event.preventDefault();if(busy)return;if(!plan){await update();return;}if(!beforeApply()){preview.textContent='请先保存当前文档，再整理标签。';return;}busy=true;submit.disabled=true;field.disabled=true;form.querySelector('.tag-rename-back').disabled=true;try{
   const result=await post('/api/tags/rename',plan);await onApplied(result);back();await load();status.textContent='已'+(result.merge?'合并':'重命名')+'，更新 '+result.count+' 份文档';
  }catch(error){preview.textContent=error.message;plan=null;submit.textContent='重新预览';submit.disabled=false;}finally{busy=false;field.disabled=false;form.querySelector('.tag-rename-back').disabled=false;}};
  update();field.focus();field.select();
 }
 input.oninput=()=>{clearTimeout(timer);version++;timer=setTimeout(()=>load(),150);};
 dialog.addEventListener('cancel',event=>{if(busy)event.preventDefault();});dialog.addEventListener('close',()=>{disposed=true;version++;clearTimeout(timer);dialog.remove();});
 dialog.addEventListener('click',event=>{if(event.target===dialog&&!busy){const box=dialog.getBoundingClientRect();if(event.clientX<box.left||event.clientX>box.right||event.clientY<box.top||event.clientY>box.bottom)dialog.close();}});
 dialog.showModal();input.focus();load();return dialog;
}
