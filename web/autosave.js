const preferenceKey='workmoire:autosave';
export function createAutosave({getState,save,onStatus}){
 let enabled=false;try{enabled=localStorage.getItem(preferenceKey)==='true';}catch{}
 let timer=0,phase='idle',attempts=0,blocked='',revision=0;
 const emit=()=>onStatus?.({enabled,phase,blocked});
 const eligible=()=>{const s=getState();return enabled&&s.authenticated&&s.current?.id&&s.dirty;};
 function queue(delay=2000,keepError=false){clearTimeout(timer);if(!eligible()||blocked)return;if(!keepError)phase='waiting';emit();timer=setTimeout(run,delay);}
 async function run(){
  timer=0;if(!eligible()||blocked)return;const s=getState();
  if(navigator.onLine===false){phase='error';blocked='offline';emit();return;}
  if(s.busy||s.composing){queue(400);return;}
  phase='saving';emit();const token=s.current,version=revision;
  try{const result=await save();if(version===revision&&getState().current===token)resultFor(result,token);}
  catch{if(version===revision&&getState().current===token)resultFor({status:'error',retryable:true},token);}
 }
 function resultFor(result,token){
  if(getState().current!==token)return;clearTimeout(timer);
  if(result?.status==='saved'){
   phase='idle';attempts=0;blocked='';emit();queue();return;
  }
  if(result?.status==='busy'){queue(500);return;}
  if(result?.status==='abandoned')return;
  phase=result?.status==='conflict'?'conflict':'error';blocked=result?.status==='conflict'?'conflict':result?.status==='unauthorized'?'auth':result?.retryable===false?'validation':'';emit();
  if(enabled&&!blocked&&eligible()){
   attempts++;if(attempts<=3)queue([2000,5000,15000][attempts-1],true);else{blocked='retry';emit();}
  }
 }
 function changed(){if(['conflict','auth','validation'].includes(blocked))return;blocked='';attempts=0;queue();}
 function setEnabled(value,persist=true){enabled=Boolean(value);clearTimeout(timer);revision++;if(persist)try{localStorage.setItem(preferenceKey,String(enabled));}catch{}if(!enabled&&phase==='waiting')phase='idle';emit();if(enabled)changed();}
 window.addEventListener('online',()=>{if(enabled&&['offline','retry',''].includes(blocked)){blocked='';attempts=0;queue(0);}});
 window.addEventListener('storage',event=>{if(event.key===preferenceKey)setEnabled(event.newValue==='true',false);});
 return {
  snapshot:()=>({enabled,phase,blocked}),setEnabled,changed,
  documentChanged(){clearTimeout(timer);revision++;attempts=0;blocked='';phase='idle';emit();},
  manualStarted(){clearTimeout(timer);revision++;phase='saving';emit();},
  manualFinished:resultFor,
 };
}

export function mountSaveControls({root,controller,save}){
 const button=root.querySelector('#save-content'),controls=document.createElement('div');controls.className='save-controls';button.before(controls);controls.append(button);
 const toggle=document.createElement('button');toggle.type='button';toggle.id='save-options';toggle.className='save-options-toggle';toggle.setAttribute('aria-label','保存设置');toggle.title='保存设置';toggle.setAttribute('aria-expanded','false');toggle.innerHTML=window.WorkmoireIcons.render('chevron');
 const menu=document.createElement('div');menu.className='save-options-menu';menu.hidden=true;menu.innerHTML='<label><input id="autosave-enabled" type="checkbox"><span>自动保存</span></label><p>停笔约 2 秒后保存已有文档。新文档首次需手动保存。</p>';
 controls.append(toggle,menu);const input=menu.querySelector('input');
 function close(){menu.hidden=true;toggle.setAttribute('aria-expanded','false');}
 function sync(){const status=controller.snapshot();input.checked=status.enabled;controls.dataset.autosave=String(status.enabled);toggle.title=status.enabled?'保存设置 · 自动保存已开启':'保存设置 · 手动保存';}
 toggle.onmousedown=event=>event.preventDefault();toggle.onclick=()=>{const open=menu.hidden;menu.hidden=!open;toggle.setAttribute('aria-expanded',String(open));sync();};
 input.onchange=()=>{controller.setEnabled(input.checked);sync();};
 const outside=event=>{if(!controls.contains(event.target))close();},escape=event=>{if(event.key==='Escape'&&!event.isComposing&&!menu.hidden){event.preventDefault();event.stopImmediatePropagation();close();toggle.focus({preventScroll:true});}};
 document.addEventListener('pointerdown',outside);document.addEventListener('keydown',escape,true);window.addEventListener('blur',close);sync();
 return {sync,destroy(){document.removeEventListener('pointerdown',outside);document.removeEventListener('keydown',escape,true);window.removeEventListener('blur',close);}};
}
