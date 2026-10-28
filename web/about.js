const icon=name=>window.WorkmoireIcons.render(name);
let current=null,pending=null;
export async function loadVersion(request){
 try{current=await request('/api/version');document.querySelector('#app-version').textContent='v'+current.version;document.querySelector('#app-version').title='当前版本 v'+current.version+' · 查看版本与更新日志';}catch{document.querySelector('#app-version').textContent='版本';}
}
export function openAbout(request){
 const existing=document.querySelector('#about-dialog');if(existing){existing.focus();return;}
 const dialog=document.createElement('dialog');dialog.id='about-dialog';dialog.className='dialog about-dialog';dialog.setAttribute('aria-label','关于 Workmoire');
 dialog.innerHTML='<div class="dialog-card about-card"><div class="dialog-head"><h2>关于 Workmoire</h2><button class="icon-button about-close" aria-label="关闭关于">'+icon('close')+'</button></div><div class="about-identity"><span class="brand-mark">'+icon('book')+'</span><div><strong>Workmoire <span>拾序</span></strong><p>学术笔记、论文阅读与文档关联</p></div></div><div class="about-current"><span>当前版本</span><strong id="about-version">正在读取…</strong><small id="about-revision"></small></div><a id="about-github" class="about-project-link" href="https://github.com/ZAIQuQ/Workmoire" target="_blank" rel="noopener noreferrer"><img class="icon" src="/static/github.svg" alt=""><span><strong>GitHub 项目</strong><small>ZAIQuQ / Workmoire</small></span>'+icon('arrow')+'</a><div class="about-release-links"><a id="about-latest" href="https://github.com/ZAIQuQ/Workmoire/releases/latest" target="_blank" rel="noopener noreferrer">最新版本 '+icon('arrow')+'</a><a id="about-changelog" href="https://github.com/ZAIQuQ/Workmoire/blob/main/CHANGELOG.md" target="_blank" rel="noopener noreferrer">更新日志 '+icon('arrow')+'</a></div><div class="about-update"><p id="about-status" role="status">正在检查 GitHub 版本…</p><button id="about-check" class="quiet-button">重新检查</button></div><details class="about-notes" open><summary>当前版本更新</summary><div id="about-notes" class="prose"></div></details><details id="about-remote-notes" class="about-notes" hidden><summary>GitHub 最新版本更新</summary><div class="prose"></div></details><footer class="about-footer">MIT License · 数据保存在你的服务器上</footer></div>';
 document.body.append(dialog);const q=s=>dialog.querySelector(s);let closed=false;
 const close=()=>dialog.close();q('.about-close').onclick=close;dialog.addEventListener('close',()=>{closed=true;dialog.remove();});dialog.addEventListener('click',event=>{if(event.target===dialog){const r=dialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)close();}});
 function notes(element,text){element.innerHTML=window.WorkmoireEditor.render(text||'此版本未附更新说明。');element.querySelectorAll('a').forEach(a=>{const href=a.getAttribute('href')||'';if(href&&!/^(?:[a-z][a-z0-9+.-]*:|\/\/|#)/i.test(href))a.href=new URL(href,'https://github.com/ZAIQuQ/Workmoire/blob/main/').href;a.target='_blank';a.rel='noopener noreferrer';});}
 function paint(data){q('#about-version').textContent='v'+data.version;q('#about-revision').textContent=data.revision?data.revision.slice(0,7):'';notes(q('#about-notes'),data.notes);}
 async function check(){
  q('#about-check').disabled=true;q('#about-status').textContent='正在检查 GitHub 版本…';
  try{pending??=request('/api/version?check=1').finally(()=>pending=null);const data=await pending;if(closed)return;current=data;paint(data);q('#about-latest').innerHTML='最新版本 '+icon('arrow');const latest=data.latest;
   q('#about-remote-notes').hidden=latest?.status!=='available'||latest.comparison==='current';
   if(latest?.status==='available'){
    q('#about-status').textContent=latest.comparison==='newer'?'有新版本 v'+latest.version:latest.comparison==='older'?'GitHub 最新发布为 v'+latest.version+'，当前部署版本较新。':'已是 GitHub 最新发布版本';
    q('#about-latest').href=latest.url;if(latest.comparison!=='current')notes(q('#about-remote-notes .prose'),latest.notes);
   }else{q('#about-status').textContent=latest?.status==='unpublished'?'GitHub 暂无正式 Release，可先查看更新日志或提交记录。':'暂时无法检查 GitHub 版本，可使用上方链接查看。';q('#about-latest').href=data.releases_url;if(latest?.status==='unpublished'){q('#about-latest').href=data.commits_url;q('#about-latest').innerHTML='最近提交 '+icon('arrow');}}
  }catch{if(!closed)q('#about-status').textContent='版本信息暂时不可用，请稍后重试。';}finally{if(!closed)q('#about-check').disabled=false;}
 }
 q('#about-check').onclick=check;dialog.showModal();if(current)paint(current);check();return dialog;
}
