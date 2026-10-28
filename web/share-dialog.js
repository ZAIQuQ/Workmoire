const icon=name=>window.WorkmoireIcons.render(name);
export function openShareDialog({request,post,getState,ensureSaved}){
 const dialog=document.createElement('dialog');dialog.className='dialog share-settings-dialog';dialog.setAttribute('aria-label','分享文档');
 const card=document.createElement('div');card.className='dialog-card';card.innerHTML='<div class="dialog-head"><h2>分享文档</h2><button type="button" class="icon-button share-close" aria-label="关闭分享">'+icon('close')+'</button></div><p class="share-version-note quiet"></p><label class="field"><span>分享链接</span><div class="share-field-row"><input id="share-link" aria-label="分享链接" readonly placeholder="生成后可复制"><button type="button" class="button secondary small" id="share-copy-link">复制链接</button></div></label><label class="field"><span>有效时间</span><select id="share-duration" aria-label="分享有效时间"><option value="1">1 天</option><option value="7" selected>7 天</option><option value="30">30 天</option><option value="0">永久</option></select><small id="share-expiry"></small></label><label class="field"><span>访问密码 · 自动生成</span><div class="share-field-row"><input id="share-owner-password" type="password" aria-label="分享访问密码" readonly autocomplete="off" placeholder="每个链接都必须使用密码"><button type="button" class="button secondary small" id="share-show-password">显示</button><button type="button" class="button secondary small" id="share-reset-password">重置</button></div><small>密码包含大小写字母、数字和符号。重置后原密码立即失效。</small></label><div class="share-dialog-status" role="status"></div><div class="share-dialog-actions"><button type="button" class="quiet-button danger" id="share-revoke">停止分享</button><button type="button" class="button secondary small" id="share-copy-all">复制链接和密码</button><button type="button" class="button primary small" id="share-create">生成分享链接</button></div>';
 dialog.append(card);document.body.append(dialog);const q=s=>card.querySelector(s);let share=null,busy=false,closed=false,publicBase='',port=5201;
 const state=()=>{const value=getState();if(!value?.item)throw new Error('文档已切换，请重新打开分享');return value;};
 function link(){if(!share)return '';const base=publicBase?new URL(publicBase):new URL(location.href);if(!publicBase){base.protocol='http:';base.port=String(port);}return new URL(share.path,base).href;}
 function paint(){
  let current;try{current=state();}catch(error){q('.share-dialog-status').textContent=error.message;return;}
  q('#share-link').value=link();q('#share-owner-password').value=share?.password||'';if(share)q('#share-duration').value=String(share.days);
  q('#share-expiry').textContent=share?(share.expires_at?'有效至 '+new Date(share.expires_at*1000).toLocaleString('zh-CN',{hour12:false}):'永久有效，可随时停止分享'):'';
  const changed=share&&share.source_updated_at!==current.item.updated_at;
  q('.share-version-note').textContent=share?'分享的是已保存的只读快照。'+(changed?'文档已有新版本；生成新链接会更新内容并使原链接失效。':'重新生成后，原链接立即失效。'):'分享当前已保存的文档及正文引用的附件。后续修改不会自动公开。';
  q('#share-create').textContent=(current.ready?'':'保存并')+(share?'生成新链接':'生成分享链接');
  for(const selector of ['.share-close','#share-duration','#share-create'])q(selector).disabled=busy;
  for(const selector of ['#share-revoke','#share-reset-password','#share-show-password'])q(selector).disabled=busy||!share;
  q('#share-copy-link').disabled=busy||!share?.active;q('#share-copy-all').disabled=busy||!share?.active;
 }
 async function load(){const item=state().item;if(!item.id){paint();return;}busy=true;paint();try{const data=await request('/api/items/'+item.id+'/share');if(closed)return;share=data.share;publicBase=data.public_base_url;port=data.port;}catch(error){q('.share-dialog-status').textContent=error.message;}finally{busy=false;paint();}}
 async function copy(value){const status=q('.share-dialog-status');try{if(navigator.clipboard&&window.isSecureContext)await navigator.clipboard.writeText(value);else{const field=document.createElement('textarea');field.value=value;field.style.cssText='position:fixed;opacity:0';dialog.append(field);field.select();const ok=document.execCommand('copy');field.remove();if(!ok)throw new Error();}status.textContent='已复制';}catch{status.textContent='浏览器未允许复制，请选择上方内容手动复制。';}}
 q('#share-copy-link').onclick=()=>copy(link());q('#share-copy-all').onclick=()=>copy('文档分享：'+link()+'\n访问密码：'+share.password+'\n'+q('#share-expiry').textContent);
 q('#share-show-password').onclick=()=>{const field=q('#share-owner-password'),show=field.type==='password';field.type=show?'text':'password';q('#share-show-password').textContent=show?'隐藏':'显示';};
 q('#share-create').onclick=async()=>{
  if(busy)return;const days=Number(q('#share-duration').value);busy=true;paint();q('.share-dialog-status').textContent='正在准备分享…';
  try{await ensureSaved();const item=state().item;const data=await post('/api/items/'+item.id+'/share',{days,base_updated_at:item.updated_at});share=data.share;publicBase=data.public_base_url;port=data.port;q('.share-dialog-status').textContent='分享链接已生成，请将链接和密码提供给接收者。';}
  catch(error){q('.share-dialog-status').textContent=error.message;}
  finally{busy=false;paint();}
 };
 async function change(action,days){if(busy||!share)return;busy=true;paint();q('.share-dialog-status').textContent='正在更新…';try{const data=await post('/api/items/'+state().item.id+'/share/settings',{share_id:share.id,revision:share.revision,action,...(days!==undefined?{days}:{})});share=data.share;q('.share-dialog-status').textContent=action==='revoke'?'分享已停止，原链接无法访问。':action==='password'?'已生成新密码，原密码和访问会话已失效。':'有效时间已更新。';}catch(error){q('.share-dialog-status').textContent=error.message;}finally{busy=false;paint();}}
 q('#share-duration').onchange=()=>{if(share)change('expiry',Number(q('#share-duration').value));};q('#share-reset-password').onclick=()=>change('password');q('#share-revoke').onclick=()=>change('revoke');q('.share-close').onclick=()=>dialog.close();
 dialog.addEventListener('cancel',event=>{if(busy)event.preventDefault();});dialog.addEventListener('close',()=>{closed=true;share=null;dialog.remove();});dialog.addEventListener('click',event=>{if(event.target===dialog&&!busy){const r=dialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)dialog.close();}});dialog.showModal();paint();load();return dialog;
}
