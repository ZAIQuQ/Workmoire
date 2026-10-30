const preferenceKey='workmoire:autosave:v2';
const retryDelays=[2000,5000,15000,30000,60000];
const permanent=new Set(['conflict','auth','validation']);
export function createAutosave({getState,save,probe,preserveDraft,onStatus}){
 let enabled=true;try{enabled=localStorage.getItem(preferenceKey)!=='false';}catch{}
 let timer=0,phase='idle',attempts=0,blocked='',revision=0,fault=null,pendingSince=0;
 const emit=()=>onStatus?.({enabled,phase,blocked,fault});
 const actionable=()=>{const s=getState();return enabled&&s.authenticated&&s.current&&(s.current.id||s.canCreate||s.current.creation_attempted)&&s.dirty;};
 const temporary=()=>fault&&!permanent.has(blocked);
 function queue(delay=2000){clearTimeout(timer);timer=0;if(!enabled||!getState().authenticated||permanent.has(blocked)||(!actionable()&&!temporary()))return;
  if(navigator.onLine===false){offline();return;}phase='waiting';emit();timer=setTimeout(run,delay);
 }
 function offline(){clearTimeout(timer);timer=0;if(!enabled||!getState().current)return;
  const first=blocked!=='offline';if(!permanent.has(blocked)){fault={kind:'network',message:'网络连接已中断'};blocked='offline';phase='error';}if(first)preserveDraft?.();emit();
 }
 async function run(){
  timer=0;const s=getState();if(!enabled||!s.authenticated||!s.current||permanent.has(blocked))return;
  if(navigator.onLine===false){offline();return;}
  if(s.busy||s.composing){queue(400);return;}
  const token=s.current,version=revision;phase='saving';emit();
  try{
   const result=actionable()?await save():fault?await probe():{status:'saved'};
   if(version===revision&&getState().current===token)resultFor(result,token);
  }catch(error){if(version===revision&&getState().current===token)resultFor({status:'error',retryable:true,kind:'network',message:error.message},token);}
 }
 function resultFor(result,token){
  if(getState().current!==token)return;clearTimeout(timer);timer=0;
  if(result?.status==='saved'){
   phase='idle';attempts=0;blocked='';pendingSince=0;
   if(!getState().dirty)fault=null;
   emit();if(actionable())queue();return;
  }
  if(result?.status==='busy'){queue(500);return;}
  if(result?.status==='abandoned')return;
  blocked=result?.status==='conflict'?'conflict':result?.status==='unauthorized'?'auth':result?.retryable===false?'validation':'';
  fault={kind:blocked||result?.kind||'server',message:String(result?.message||'暂时无法完成保存').slice(0,180)};phase=blocked==='conflict'?'conflict':'error';preserveDraft?.();emit();
  if(enabled&&!permanent.has(blocked)){attempts++;queue(retryDelays[Math.min(attempts-1,retryDelays.length-1)]);}
 }
 function changed(){
  if(!enabled)return;
  if(permanent.has(blocked))return;
  if(navigator.onLine===false){offline();return;}
  if(fault){if(!timer&&phase!=='saving')queue(2000);else emit();return;}
  if(!actionable()){pendingSince=0;return;}if(!pendingSince)pendingSince=Date.now();queue(Math.min(2000,Math.max(0,10000-(Date.now()-pendingSince))));
 }
 function setEnabled(value,persist=true){enabled=Boolean(value);clearTimeout(timer);timer=0;if(persist)try{localStorage.setItem(preferenceKey,String(enabled));}catch{}if(!enabled&&phase==='waiting')phase='idle';emit();if(enabled)changed();}
 window.addEventListener('offline',offline);
 window.addEventListener('online',()=>{if(enabled&&!permanent.has(blocked)){blocked='';attempts=0;queue(0);}});
 window.addEventListener('storage',event=>{if(event.key===preferenceKey)setEnabled(event.newValue!=='false',false);});
 return {
  snapshot:()=>({enabled,phase,blocked,fault}),setEnabled,changed,
  retry(){if(!permanent.has(blocked)){blocked='';attempts=0;queue(0);}},
  availabilityFailed(result){if(enabled&&getState().current&&!fault){fault={kind:result?.kind||'network',message:'服务连接异常'};phase='error';preserveDraft?.();emit();queue(2000);}},
  documentChanged(){clearTimeout(timer);timer=0;revision++;attempts=0;blocked='';phase='idle';pendingSince=0;fault=enabled&&navigator.onLine===false?{kind:'network',message:'网络连接已中断'}:null;emit();},
  manualStarted(){clearTimeout(timer);timer=0;revision++;phase='saving';emit();},
  manualFinished:resultFor,
 };
}

export function mountSyncWarning({controller,getState,save,copyDraft,login,resolveConflict}){
 const notice=document.createElement('aside');notice.id='sync-warning';notice.className='sync-warning';notice.hidden=true;notice.setAttribute('role','alert');notice.setAttribute('aria-live','assertive');
 notice.innerHTML='<strong class="sync-warning-title"></strong><p class="sync-warning-guidance">建议暂时停止编辑，等待同步恢复。</p><small class="sync-warning-detail"></small><div class="sync-warning-actions"><button type="button" id="sync-retry">立即重试</button><button type="button" id="sync-copy">复制当前内容</button></div>';document.body.append(notice);
 const title=notice.querySelector('strong'),detail=notice.querySelector('small'),retry=notice.querySelector('#sync-retry'),copy=notice.querySelector('#sync-copy');
 function text(el,value){if(el.textContent!==value)el.textContent=value;}
 function position(){if(notice.hidden)return;const rect=document.querySelector('.document-topline')?.getBoundingClientRect(),right=rect?.width?Math.max(8,innerWidth-rect.right):12,bottom=Math.max(rect?.bottom||0,...['#draft-notice','#conflict-notice'].map(selector=>{const r=document.querySelector(selector)?.getBoundingClientRect();return r?.height?r.bottom:0}));notice.style.right=right+'px';notice.style.top=(rect?.height?Math.min(bottom+8,Math.max(8,innerHeight-notice.offsetHeight-8)):16)+'px';}
 function sync(){const s=getState(),status=controller.snapshot(),fault=status.fault;notice.hidden=!fault||!s.current;if(notice.hidden)return;
  const titles={network:s.dirty?'网络异常，自动保存失败':'网络异常，自动同步已暂停',server:s.dirty?'服务异常，自动保存失败':'服务异常，自动同步不可用',auth:'登录已失效，自动同步已暂停',conflict:'版本冲突，自动同步已暂停',validation:'内容无法保存，自动同步异常'};
  text(title,titles[fault.kind]||'自动保存失败，同步异常');
  const local=s.dirty?(s.draftError?'本机草稿也保存失败，请先复制内容备份。':s.draftCurrent?'未同步内容已保留为本机草稿。':'正在保留本机草稿，请勿关闭页面。'):'当前没有未保存改动。';
  const reason=fault.kind==='auth'?'请重新登录后恢复本机草稿。':fault.kind==='conflict'?'请先处理其他窗口产生的新版本。':fault.kind==='validation'?fault.message+'。':status.phase==='saving'?'正在后台重试。':navigator.onLine===false?'网络恢复后将自动重试。':status.enabled?'正在等待后台重试。':'';
  text(detail,reason+local);text(retry,fault.kind==='auth'?'重新登录':fault.kind==='conflict'?'打开最新版本':status.phase==='saving'?'正在重试…':'立即重试');retry.disabled=s.busy||status.phase==='saving'||navigator.onLine===false;copy.hidden=!s.dirty;copy.disabled=s.composing;position();
 }
 retry.onclick=()=>{const kind=controller.snapshot().fault?.kind;if(kind==='auth')login();else if(kind==='conflict')resolveConflict();else if(getState().dirty)save();else controller.retry();};copy.onclick=copyDraft;
 window.addEventListener('resize',position);sync();return {sync};
}

export function mountSaveControls({root,controller,save}){
 const button=root.querySelector('#save-content'),controls=document.createElement('div');controls.className='save-controls';button.before(controls);controls.append(button);
 const toggle=document.createElement('button');toggle.type='button';toggle.id='save-options';toggle.className='save-options-toggle';toggle.setAttribute('aria-label','保存设置');toggle.title='保存设置';toggle.setAttribute('aria-expanded','false');toggle.innerHTML=window.WorkmoireIcons.render('chevron');
 const menu=document.createElement('div');menu.className='save-options-menu';menu.hidden=true;menu.innerHTML='<label><input id="autosave-enabled" type="checkbox"><span>自动保存</span></label><p>有改动时在后台自动保存，新文档也会自动建立。同步异常会在右上角持续提醒。</p>';
 controls.append(toggle,menu);const input=menu.querySelector('input');
 function close(){menu.hidden=true;toggle.setAttribute('aria-expanded','false');}
 function sync(){const status=controller.snapshot();input.checked=status.enabled;controls.dataset.autosave=String(status.enabled);toggle.title=status.enabled?'保存设置 · 自动保存已开启':'保存设置 · 手动保存';}
 toggle.onmousedown=event=>event.preventDefault();toggle.onclick=()=>{const open=menu.hidden;menu.hidden=!open;toggle.setAttribute('aria-expanded',String(open));sync();};
 input.onchange=()=>{controller.setEnabled(input.checked);sync();};
 const outside=event=>{if(!controls.contains(event.target))close();},escape=event=>{if(event.key==='Escape'&&!event.isComposing&&!menu.hidden){event.preventDefault();event.stopImmediatePropagation();close();toggle.focus({preventScroll:true});}};
 document.addEventListener('pointerdown',outside);document.addEventListener('keydown',escape,true);window.addEventListener('blur',close);sync();
 return {sync,destroy(){document.removeEventListener('pointerdown',outside);document.removeEventListener('keydown',escape,true);window.removeEventListener('blur',close);}};
}
