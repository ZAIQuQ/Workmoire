const icon=name=>window.WorkmoireIcons.render(name);
const nameOf=value=>String(value).normalize('NFKC').trim().replace(/^#+/,'').trim().replace(/\s+/g,' ');
const key=value=>nameOf(value).toLowerCase();
const button=(text,cls)=>{const el=document.createElement('button');el.type='button';el.className=cls;el.textContent=text;return el;};
let nextId=0;

export function mountTagPicker(host,{value='',request,onChange,title=()=>'',editable=true}){
 let current=value,open=false,destroyed=false,readOnly=!editable,version=0,timer,active=0,choices=[],known=[];
 const chips=document.createElement('div');chips.className='document-tag-chips';
 const trigger=button('添加标签','tag-add');trigger.setAttribute('aria-expanded','false');
 const panel=document.createElement('div');panel.className='tag-picker';panel.hidden=true;
 const input=document.createElement('input');input.placeholder='搜索或创建标签';input.setAttribute('aria-label','搜索或创建标签');input.setAttribute('role','combobox');input.setAttribute('aria-autocomplete','list');input.autocomplete='off';
 const selected=document.createElement('div');selected.className='tag-picker-selected';
 const caption=document.createElement('div');caption.className='tag-picker-caption';
 const list=document.createElement('div');list.className='tag-options';list.id='tag-options-'+(++nextId);list.setAttribute('role','listbox');input.setAttribute('aria-controls',list.id);
 const status=document.createElement('div');status.className='tag-picker-status';status.setAttribute('role','status');
 panel.append(input,selected,caption,list,status);host.append(chips,trigger,panel);
 const tags=()=>current.split(',').filter(Boolean);
 function render(){
  const values=tags();chips.replaceChildren();selected.replaceChildren();
  values.slice(0,3).forEach(tag=>{const chip=button(tag,'document-tag');chip.title=tag;chip.onclick=show;chips.append(chip);});
  if(values.length>3){const more=button('+'+(values.length-3),'document-tag tag-overflow');more.setAttribute('aria-label','查看全部 '+values.length+' 个标签');more.onclick=show;chips.append(more);}
  for(const tag of values){const chip=document.createElement('span');chip.className='selected-tag';const label=document.createElement('span');label.textContent=tag;chip.append(label);if(!readOnly){const remove=button('','tag-remove');remove.innerHTML=icon('close');remove.setAttribute('aria-label','移除标签 '+tag);remove.onclick=()=>{change(values.filter(t=>t!==tag));input.focus();};chip.append(remove);}selected.append(chip);}
  selected.hidden=!values.length;trigger.hidden=readOnly;trigger.innerHTML=icon('plus')+'添加标签';host.hidden=readOnly&&!values.length;
 }
 function change(values){current=values.join(',');render();onChange(current);load();}
 function add(raw){
  const additions=String(raw).replaceAll('，',',').split(',').map(nameOf).filter(Boolean),values=tags();
  if(additions.some(tag=>Array.from(tag).length>32)){status.textContent='标签名称最多 32 个字符';return;}
  for(let tag of additions){tag=known.find(item=>key(item.tag)===key(tag))?.tag||tag;if(!values.some(value=>key(value)===key(tag)))values.push(tag);}
  if(values.length>12){status.textContent='每份文档最多 12 个标签';return;}
  input.value='';change(values);input.focus();
 }
 function paint(){
  list.replaceChildren();input.removeAttribute('aria-activedescendant');
  choices.forEach((choice,index)=>{const row=button('','tag-option');row.id=list.id+'-'+index;row.setAttribute('role','option');row.setAttribute('aria-selected',String(index===active));row.innerHTML=icon(choice.create?'plus':'tag');const label=document.createElement('span');label.textContent=choice.create?'创建「'+choice.tag+'」':choice.tag;const detail=document.createElement('small');detail.textContent=choice.create?'Enter':choice.title_match?'标题匹配':choice.related?'常一起使用':choice.count+' 份';row.append(label,detail);row.onmousedown=event=>event.preventDefault();row.onclick=()=>add(choice.tag);list.append(row);});
  if(choices.length)input.setAttribute('aria-activedescendant',list.id+'-'+active);
 }
 async function load(){
  const mine=++version;if(!open||readOnly)return;
  const query=nameOf(input.value);choices=[];paint();status.textContent='';caption.textContent=query?'匹配的标签':'建议标签';
  try{
   const params=new URLSearchParams({limit:'20',q:query,title:title().slice(0,200),context:tags().at(-1)||''});
   const result=await request('/api/tags?'+params);if(destroyed||mine!==version||!open)return;
   known=result.tags;choices=known.filter(item=>!tags().some(tag=>key(tag)===key(item.tag)));
   const exists=known.some(item=>key(item.tag)===key(query))||tags().some(tag=>key(tag)===key(query));
   if(query&&!exists&&!/[,，]/.test(query)&&Array.from(query).length<=32&&tags().length<12)choices.push({tag:query,create:true});
   active=0;paint();if(!choices.length)status.textContent=/[,，]/.test(query)?'按 Enter 添加这些标签':query?'没有其他匹配标签':'输入名称创建标签';
  }catch(error){if(mine===version){choices=[];paint();status.textContent=error.message;}}
 }
 function show(){if(open){hide();return;}open=true;panel.hidden=false;trigger.setAttribute('aria-expanded','true');input.setAttribute('aria-expanded','true');input.hidden=readOnly;caption.hidden=readOnly;list.hidden=readOnly;render();if(!readOnly){input.value='';input.focus();load();}}
 function hide(){open=false;version++;clearTimeout(timer);panel.hidden=true;trigger.setAttribute('aria-expanded','false');input.setAttribute('aria-expanded','false');}
 input.oninput=event=>{clearTimeout(timer);version++;choices=[];paint();if(!event.isComposing)timer=setTimeout(load,120);};
 input.onkeydown=event=>{
  if(event.isComposing)return;
  if(event.key==='Escape'){event.preventDefault();event.stopPropagation();hide();trigger.focus();}
  if(['ArrowDown','ArrowUp'].includes(event.key)&&choices.length){event.preventDefault();active=(active+(event.key==='ArrowDown'?1:-1)+choices.length)%choices.length;paint();list.children[active]?.scrollIntoView({block:'nearest'});}
  if(event.key==='Enter'){event.preventDefault();if(/[,，]/.test(input.value))add(input.value);else if(choices[active])add(choices[active].tag);}
 };
 host.onkeydown=event=>{if(event.key==='Escape'&&open){event.preventDefault();event.stopPropagation();hide();}};
 const outside=event=>{if(!host.contains(event.target))hide();};document.addEventListener('pointerdown',outside);trigger.onclick=show;render();
 return {value:()=>current,setValue(value){current=value;render();if(open)load();},setEditable(value){readOnly=!value;hide();render();},destroy(){destroyed=true;clearTimeout(timer);version++;document.removeEventListener('pointerdown',outside);host.onkeydown=null;host.replaceChildren();}};
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
    const row=document.createElement('div');row.className='tag-library-row';const pick=button('','tag-library-pick');pick.innerHTML=icon('tag');const label=document.createElement('span');label.textContent=item.tag;pick.append(label);pick.onclick=()=>choose(item.tag);
    const count=document.createElement('span');count.className='tag-use-count';count.textContent=item.count;
    const edit=button('','tag-library-edit');edit.innerHTML=icon('write');edit.title='重命名或合并';edit.setAttribute('aria-label','整理标签 '+item.tag);edit.onclick=()=>editTag(item);row.append(pick,count,edit);root.append(row);
   }
   if(next!==null){const more=button('加载更多','quiet-button');more.onclick=()=>load(true);pages.append(more);}
  }catch(error){if(mine===version)status.textContent=error.message;}
 }
 function editTag(item){
  if(busy)return;
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
