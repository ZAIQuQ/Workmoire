export function mountEditorToolbar(root,editor){
 const font=root.querySelector('#body-font'),colorMenu=root.querySelector('.text-color-menu'),input=root.querySelector('#text-color'),summary=colorMenu.querySelector('summary');
 const listeners=[];let tooltipTarget=null,tipTimer=0;
 const listen=(target,event,fn,options)=>{target.addEventListener(event,fn,options);listeners.push(()=>target.removeEventListener(event,fn,options));};
 const tip=document.createElement('div');tip.className='editor-tooltip';tip.id='editor-control-tooltip';tip.setAttribute('role','tooltip');tip.hidden=true;document.body.append(tip);
 for(const el of root.querySelectorAll('.editor-toolbar [title],.table-toolbar [title],.document-actions [title],.view-modes [title]')){el.dataset.tooltip=el.title;el.removeAttribute('title');}
 function hideTip(){clearTimeout(tipTimer);tip.hidden=true;if(tooltipTarget?.getAttribute('aria-describedby')===tip.id)tooltipTarget.removeAttribute('aria-describedby');tooltipTarget=null;}
 function showTip(target,delay){hideTip();tooltipTarget=target;tipTimer=setTimeout(()=>{if(!target.isConnected)return;tip.textContent=target.dataset.tooltip;tip.hidden=false;const anchor=target.getBoundingClientRect(),width=tip.offsetWidth,height=tip.offsetHeight;tip.style.left=Math.max(8,Math.min(anchor.left+(anchor.width-width)/2,innerWidth-width-8))+'px';tip.style.top=(anchor.top>height+12?anchor.top-height-7:Math.min(innerHeight-height-8,anchor.bottom+7))+'px';target.setAttribute('aria-describedby',tip.id);},delay);}
 listen(root,'pointerover',event=>{if(event.pointerType==='touch')return;const target=event.target.closest('[data-tooltip]');if(target&&target!==tooltipTarget)showTip(target,300);});
 listen(root,'pointerout',event=>{if(tooltipTarget&&!tooltipTarget.contains(event.relatedTarget))hideTip();});
 listen(root,'focusin',event=>{const target=event.target.closest('[data-tooltip]');if(target&&target.matches(':focus-visible'))showTip(target,0);});
 listen(root,'focusout',hideTip);listen(document,'pointerdown',hideTip);listen(document,'keydown',event=>{if(event.key==='Escape')hideTip();});listen(window,'resize',hideTip);listen(document,'scroll',hideTip,{capture:true,passive:true});
 function hex(value){if(/^#[\da-f]{6}$/i.test(value||''))return value.toLowerCase();if(/^#[\da-f]{3}$/i.test(value||''))return '#'+value.slice(1).split('').map(c=>c+c).join('').toLowerCase();const rgb=/^rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)$/.exec(value||'');return rgb?'#'+rgb.slice(1).map(n=>Number(n).toString(16).padStart(2,'0')).join(''):'#252a34';}
 function sync(){
  font.value=editor.bodyFont();const selected=editor.tiptap.getAttributes('textStyle').color||'',value=hex(selected);
  summary.style.setProperty('--selection-color',value);if(document.activeElement!==input)input.value=value;
  for(const button of colorMenu.querySelectorAll('[data-text-color]'))button.setAttribute('aria-pressed',String(button.dataset.textColor?(selected&&hex(button.dataset.textColor)===value):!selected));
 }
 listen(font,'change',()=>{editor.setBodyFont(font.value);sync();});
 for(const button of colorMenu.querySelectorAll('[data-text-color]')){
  listen(button,'mousedown',event=>event.preventDefault());
  listen(button,'click',()=>{editor.setColor(button.dataset.textColor||null);colorMenu.open=false;sync();});
 }
 listen(input,'input',()=>{editor.setColor(input.value,{focus:false});summary.style.setProperty('--selection-color',input.value);});
 listen(colorMenu,'toggle',()=>{if(colorMenu.open)sync();});sync();
 return {sync,destroy(){hideTip();listeners.forEach(fn=>fn());tip.remove();}};
}
