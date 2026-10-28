const icon=name=>window.WorkmoireIcons.render(name);

export function openBlogImport({post,assistantAvailable,onUse}){
 const dialog=document.createElement('dialog');dialog.className='dialog blog-import-dialog';dialog.setAttribute('aria-label','整理博客');
 const card=document.createElement('div');card.className='dialog-card blog-import-card';
 card.innerHTML='<div class="dialog-head"><h2>整理博客</h2><button type="button" class="icon-button blog-close" aria-label="关闭博客整理">'+icon('close')+'</button></div><p class="dialog-note">粘贴文章链接，保留标题、作者和来源，并生成简短摘要。</p><label class="field"><span>博客链接</span><div class="blog-reference-row"><input id="blog-reference" type="url" placeholder="https://…" aria-label="博客链接" required><button type="button" id="blog-read" class="button secondary">读取链接</button></div></label><div class="blog-source-status" role="status"></div><a class="blog-original quiet-button" target="_blank" rel="noopener noreferrer" hidden>打开原文</a><section class="blog-information" hidden><label class="field"><span>标题</span><input id="blog-title" maxlength="200" aria-label="博客标题" required></label><div class="blog-metadata-grid"><label class="field"><span>作者</span><input id="blog-author" maxlength="200" aria-label="博客作者" placeholder="未提供"></label><label class="field"><span>来源平台</span><input id="blog-site" maxlength="100" aria-label="来源平台"></label><label class="field"><span>发布日期</span><input id="blog-date" type="date" aria-label="发布日期"></label></div><details class="blog-manual"><summary>粘贴或补充正文</summary><label class="field"><span>正文</span><textarea id="blog-text" rows="7" maxlength="60000" aria-label="博客正文" placeholder="来源无法自动读取时，可粘贴文章正文。"></textarea></label></details><div class="blog-generate-row"><button type="button" id="blog-generate" class="button secondary">'+icon('spark')+'生成简要摘要</button><span class="blog-model-status quiet"></span></div></section><p class="blog-error error" role="alert"></p><section class="blog-result" hidden><div class="section-label">摘要预览</div><div class="blog-preview prose"></div></section><div class="dialog-actions"><button type="button" id="blog-use" class="button primary" disabled>放入文档</button></div>';
 const head=card.firstElementChild,actions=card.lastElementChild,scroll=document.createElement('div');scroll.className='blog-import-scroll';for(const child of [...card.children])if(child!==head&&child!==actions)scroll.append(child);card.replaceChildren(head,scroll,actions);dialog.append(card);document.body.append(dialog);
 const q=selector=>card.querySelector(selector),reference=q('#blog-reference'),info=q('.blog-information'),status=q('.blog-source-status'),error=q('.blog-error'),preview=q('.blog-preview'),result=q('.blog-result');
 let article=null,draft=null,busy=false,closed=false;
 const values=()=>({reference:reference.value.trim(),title:q('#blog-title').value.trim(),author:q('#blog-author').value.trim(),site:q('#blog-site').value.trim(),published_at:q('#blog-date').value,text:q('#blog-text').value});
 function controls(){
  q('#blog-read').disabled=busy;q('.blog-close').disabled=busy;
  for(const field of card.querySelectorAll('input,textarea'))field.disabled=busy;
  q('#blog-generate').disabled=busy||!assistantAvailable||!article||!q('#blog-title').value.trim()||(q('#blog-text').value.trim().length<80&&(article.text||'').length<80);
  q('#blog-use').disabled=busy||!article||!q('#blog-title').value.trim();q('#blog-use').textContent=draft?'放入文档':'仅建立来源档案';
  q('.blog-model-status').textContent=assistantAvailable?'':'当前未启用整理助手，可先保存来源。';
 }
 function invalidate(){draft=null;result.hidden=true;preview.replaceChildren();controls();}
 function valid(){if(!reference.reportValidity())return false;if(!q('#blog-title').reportValidity())return false;return true;}
 reference.oninput=()=>{article=null;draft=null;info.hidden=true;result.hidden=true;q('.blog-original').hidden=true;status.textContent='';error.textContent='';controls();};
 for(const field of info.querySelectorAll('input,textarea'))field.oninput=invalidate;
 q('#blog-read').onclick=async()=>{
  if(busy||!reference.reportValidity())return;busy=true;controls();error.textContent='';status.textContent='正在读取文章…';result.hidden=true;draft=null;q('#blog-read').textContent='正在读取…';
  try{const data=await post('/api/blogs/lookup',{reference:reference.value.trim()});if(closed)return;article=data.article;q('.blog-original').href=article.url;q('.blog-original').hidden=false;
   for(const [selector,key] of [['#blog-title','title'],['#blog-author','author'],['#blog-site','site'],['#blog-date','published_at']])q(selector).value=article[key]||'';
   q('#blog-text').value='';info.hidden=false;q('.blog-manual').open=!article.text;
   status.textContent=article.text?'已读取'+(article.scope==='partial_text'?'部分':'')+'正文 · '+article.text.length.toLocaleString()+' 字符':article.message;
   status.classList.toggle('needs-input',!article.text);
  }catch(e){article=null;info.hidden=true;q('.blog-original').hidden=true;error.textContent=e.message;status.textContent='';}
  finally{busy=false;q('#blog-read').textContent='读取链接';controls();}
 };
 q('#blog-generate').onclick=async()=>{
  if(busy||!valid())return;busy=true;controls();error.textContent='';q('#blog-generate').textContent='正在生成摘要…';
  try{draft=await post('/api/blogs/draft',values());if(closed)return;preview.innerHTML=window.WorkmoireEditor.render(draft.notes||draft.content);q('.blog-original').href=draft.article.url;result.hidden=false;result.scrollIntoView({block:'nearest'});}
  catch(e){draft=null;result.hidden=true;error.textContent=e.message;}
  finally{busy=false;q('#blog-generate').innerHTML=icon('spark')+'生成简要摘要';controls();}
 };
 q('#blog-use').onclick=async()=>{
  if(busy||!valid())return;busy=true;controls();error.textContent='';
  try{const prepared=draft||await post('/api/blogs/draft',{...values(),summarize:false});if(closed)return;if(await onUse(prepared)!==false)dialog.close();}
  catch(e){error.textContent=e.message;}
  finally{busy=false;controls();}
 };
 q('.blog-close').onclick=()=>dialog.close();dialog.addEventListener('cancel',event=>{if(busy)event.preventDefault();});dialog.addEventListener('close',()=>{closed=true;dialog.remove();});dialog.addEventListener('click',event=>{if(event.target===dialog&&!busy){const r=dialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)dialog.close();}});
 dialog.showModal();controls();reference.focus();return dialog;
}
