const match=/^\/s\/([A-Za-z0-9_-]{43})\/?$/.exec(location.pathname);
const $=selector=>document.querySelector(selector);
let editor=null,expires=0,retryTimer=0;
function mountShareOutline(){
 const rail=$('#share-outline'),toggle=$('#share-outline-toggle'),article=$('#share-article'),scroll=editor?.view.dom.closest('.rich-editor-scroll');if(!rail||!toggle||!scroll||!editor)return ()=>{};
 rail.innerHTML='<div class="share-outline-heading">目录</div><nav class="share-outline-nav"><ol></ol></nav>';const list=rail.querySelector('ol');let entries=[],positions=[],active=-1,frame=0;
 function refresh(){const headings=editor.outline(),base=Math.min(...headings.map(h=>h.level),6);while(entries.length<headings.length){const button=document.createElement('button'),li=document.createElement('li');button.type='button';button.dataset.index=String(entries.length);li.append(button);list.append(li);entries.push(button);}while(entries.length>headings.length)entries.pop().parentElement.remove();headings.forEach((heading,index)=>{const button=entries[index];button.textContent=heading.title.trim()||'未命名标题';button.dataset.level=heading.level;button.style.setProperty('--outline-indent',String((heading.level-base)*12)+'px');button.title=button.textContent;button.onclick=()=>{const node=editor.view.nodeDOM(heading.pos);if(node instanceof HTMLElement){node.scrollIntoView({behavior:'smooth',block:'start'});button.focus({preventScroll:true});}};});positions=headings.map((heading,index)=>{const node=editor.view.nodeDOM(heading.pos);return {index,top:node?.getBoundingClientRect().top+scroll.scrollTop||0};});}
 function update(){frame=0;if(!positions.length)return;const top=scroll.scrollTop+28;let index=0;positions.forEach((position,i)=>{if(position.top<=top)index=i;});if(index===active)return;entries[active]?.removeAttribute('aria-current');active=index;entries[active]?.setAttribute('aria-current','location');}
 function schedule(){if(!frame)frame=requestAnimationFrame(update);}
 const onScroll=()=>schedule(),onUpdate=()=>{refresh();schedule()},onToggle=()=>{const open=article.dataset.outlineOpen!=='true';article.dataset.outlineOpen=String(open);toggle.setAttribute('aria-expanded',String(open));};
 scroll.addEventListener('scroll',onScroll,{passive:true});editor.tiptap.on('update',onUpdate);toggle.onclick=onToggle;article.dataset.outlineOpen='true';toggle.setAttribute('aria-expanded','true');refresh();schedule();
 return ()=>{scroll.removeEventListener('scroll',onScroll);editor.tiptap.off('update',onUpdate);cancelAnimationFrame(frame);};
}
function gate(message='',needsPassword=false){
 editor?.destroy();editor=null;$('#shared-content').replaceChildren();$('#share-article').hidden=true;$('#share-gate').hidden=false;$('#share-message').textContent=message;document.title='Workmoire · 文档分享';
 $('#share-outline').replaceChildren();$('#share-article').dataset.outlineOpen='true';
 $('#share-form').hidden=!needsPassword;$('#share-gate-hint').hidden=!needsPassword;$('.share-lock').hidden=!needsPassword;
 $('#share-gate-title').textContent=needsPassword?'访问分享文档':'无法打开分享文档';
 $('#share-unlock').disabled=!needsPassword;
}
async function read(){
 const response=await fetch('/s/'+match[1]+'/document',{credentials:'same-origin',cache:'no-store'});const data=await response.json();
 if(!response.ok){gate(response.status===401?'':data.error||'分享暂时不可用',response.status===401);return;}
 const module='/static/vendor/editor.js?v=20261030-reading-tools';await import(module);
 editor?.destroy();$('#share-gate').hidden=true;$('#share-article').hidden=false;$('#shared-title').textContent=data.title;document.title=data.title+' · 文档分享';
 $('#shared-version').textContent='分享于 '+new Date(data.created_at*1000).toLocaleDateString('zh-CN');
 editor=window.WorkmoireEditor.mount($('#shared-content'),{richContent:data.rich_content,editable:false,copy:async text=>{try{await navigator.clipboard.writeText(text);}catch{const input=document.createElement('textarea');input.value=text;document.body.append(input);input.select();document.execCommand('copy');input.remove();}}});editor.setEditable(false);editor.view.dom.setAttribute('role','document');editor.view.dom.setAttribute('aria-label','分享的文档正文');mountShareOutline();
 expires=Math.min(data.expires_at||Infinity,data.session_expires_at||Infinity)*1000;
}
$('#share-form').onsubmit=async event=>{
 event.preventDefault();const button=$('#share-unlock'),password=$('#share-password');button.disabled=true;$('#share-message').textContent='正在验证…';
 try{const response=await fetch('/s/'+match[1]+'/unlock',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:password.value})});const data=await response.json();
  if(!response.ok){$('#share-message').textContent=data.error||'无法打开分享';if(response.status===429){const seconds=Math.max(1,Number(response.headers.get('Retry-After'))||60);clearTimeout(retryTimer);retryTimer=setTimeout(()=>button.disabled=false,Math.min(seconds,600)*1000);return;}button.disabled=false;return;}
  password.value='';await read();button.disabled=false;
 }catch{gate('网络连接失败，请稍后重试',true);button.disabled=false;}
};
if(match)read().catch(()=>gate('分享暂时不可用，请稍后重试'));else gate('分享链接无效');
function checkExpiry(){if(editor&&Date.now()>=expires){gate('正在检查分享状态…');read().catch(()=>gate('分享暂时不可用，请稍后重试'));}}
setInterval(checkExpiry,10000);
document.addEventListener('visibilitychange',()=>{if(!document.hidden)checkExpiry();});
