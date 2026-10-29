const match=/^\/s\/([A-Za-z0-9_-]{43})\/?$/.exec(location.pathname);
const $=selector=>document.querySelector(selector);
let editor=null,expires=0,retryTimer=0;
function gate(message='',needsPassword=false){
 editor?.destroy();editor=null;$('#shared-content').replaceChildren();$('#share-article').hidden=true;$('#share-gate').hidden=false;$('#share-message').textContent=message;document.title='Workmoire · 文档分享';
 $('#share-form').hidden=!needsPassword;$('#share-gate-hint').hidden=!needsPassword;$('.share-lock').hidden=!needsPassword;
 $('#share-gate-title').textContent=needsPassword?'访问分享文档':'无法打开分享文档';
 $('#share-unlock').disabled=!needsPassword;
}
async function read(){
 const response=await fetch('/s/'+match[1]+'/document',{credentials:'same-origin',cache:'no-store'});const data=await response.json();
 if(!response.ok){gate(response.status===401?'':data.error||'分享暂时不可用',response.status===401);return;}
 const module='/static/vendor/editor.js?v=20261029-reading-desk';await import(module);
 editor?.destroy();$('#share-gate').hidden=true;$('#share-article').hidden=false;$('#shared-title').textContent=data.title;document.title=data.title+' · 文档分享';
 $('#shared-version').textContent='分享于 '+new Date(data.created_at*1000).toLocaleDateString('zh-CN');
 editor=window.WorkmoireEditor.mount($('#shared-content'),{richContent:data.rich_content,editable:false,copy:async text=>{try{await navigator.clipboard.writeText(text);}catch{const input=document.createElement('textarea');input.value=text;document.body.append(input);input.select();document.execCommand('copy');input.remove();}}});editor.setEditable(false);editor.view.dom.setAttribute('role','document');editor.view.dom.setAttribute('aria-label','分享的文档正文');
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
