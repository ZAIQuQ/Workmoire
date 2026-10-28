const icon=name=>window.WorkmoireIcons.render(name);

export function openPaperImport({request,post,assistantAvailable,onUse}){
 const dialog=document.createElement('dialog');dialog.className='dialog paper-import-dialog';dialog.setAttribute('aria-label','新建论文资料');
 const card=document.createElement('div');card.className='dialog-card paper-import-card';
 card.innerHTML='<div class="dialog-head"><h2>新建论文资料</h2><button type="button" class="icon-button paper-close" aria-label="关闭论文导入">'+icon('close')+'</button></div><div class="paper-import-scroll"><p class="dialog-note">上传 PDF，或提供链接自动下载。同时提供时，始终使用你上传的 PDF。</p><label class="field"><span>论文链接（可选）</span><input id="paper-reference" type="url" placeholder="https://…" aria-label="论文链接" maxlength="3000"></label><label class="paper-upload-zone"><span>'+icon('upload')+'上传 PDF</span><small>可单独上传，也可用来替换自动下载的文件</small><input id="paper-pdf-input" type="file" accept="application/pdf,.pdf" aria-label="选择论文 PDF"></label><div class="paper-selected-upload" hidden><span></span><button type="button" class="quiet-button" id="paper-clear-upload">移除选择</button></div><button id="paper-prepare" type="button" class="button secondary">导入论文</button><div class="paper-import-status" role="status"></div><div class="paper-source-links" hidden><a id="paper-open-source" class="quiet-button" target="_blank" rel="noopener noreferrer">打开原文</a><a id="paper-open-download" class="quiet-button" target="_blank" rel="noopener noreferrer">打开 PDF 链接</a></div><section class="paper-prepared" hidden><label class="field"><span>论文标题</span><input id="paper-title" maxlength="200" aria-label="论文标题" required></label><label class="field"><span>作者（可选）</span><input id="paper-author" maxlength="300" aria-label="论文作者"></label><div class="paper-selected-info"></div><details class="paper-file-preview" open><summary>核对所选 PDF</summary><iframe title="所选论文 PDF 预览"></iframe></details><div class="paper-analysis-actions"><button id="paper-generate" type="button" class="button secondary">'+icon('spark')+'生成阅读档案</button><span class="paper-text-status quiet"></span></div></section><p class="paper-import-error error" role="alert"></p><section class="paper-analysis-result" hidden><div class="section-label">阅读档案预览</div><div class="prose paper-analysis-preview"></div></section></div><div class="dialog-actions"><button id="paper-use" type="button" class="button primary" disabled>放入编辑器</button></div>';
 dialog.append(card);document.body.append(dialog);const q=selector=>card.querySelector(selector),reference=q('#paper-reference'),fileInput=q('#paper-pdf-input'),status=q('.paper-import-status'),error=q('.paper-import-error');
 let selected=null,prepared=null,extracted=null,draft=null,busy=false,closed=false;const owned=new Set();
 async function discard(ids=[...owned]){for(const id of ids){try{await request('/api/files/'+id,{method:'DELETE'});owned.delete(id);}catch{/* Leave recoverable, unassociated files in attachment management if cleanup fails. */}}}
 function controls(){
  q('.paper-close').disabled=busy;reference.disabled=busy;fileInput.disabled=busy;q('#paper-clear-upload').disabled=busy;q('#paper-prepare').disabled=busy||(!selected&&!reference.value.trim());
  q('#paper-title').disabled=busy;q('#paper-author').disabled=busy;
  q('#paper-use').disabled=busy||!prepared||!q('#paper-title').value.trim();
  const readable=(extracted?.text||'').replace(/\[第 \d+ 页\]/g,'').trim().length>=80;
  q('#paper-generate').disabled=busy||!prepared||!readable||!assistantAvailable;
  q('.paper-text-status').textContent=!prepared?'':!readable?'未提取到足够文字，可先建立资料并手动阅读。':!assistantAvailable?'当前未配置整理助手，可先建立资料。':(extracted.truncated?'已提取部分文字':'已提取文字')+' · '+extracted.pages_read+' / '+extracted.page_count+' 页';
 }
 function invalidateSource(){prepared=null;extracted=null;draft=null;q('.paper-prepared').hidden=true;q('.paper-analysis-result').hidden=true;q('.paper-source-links').hidden=true;q('.paper-file-preview iframe').removeAttribute('src');status.textContent='';error.textContent='';controls();}
 reference.oninput=invalidateSource;
 fileInput.onchange=()=>{selected=fileInput.files[0]||null;invalidateSource();q('.paper-selected-upload').hidden=!selected;q('.paper-selected-upload span').textContent=selected?selected.name:'';};
 q('#paper-clear-upload').onclick=()=>{selected=null;fileInput.value='';q('.paper-selected-upload').hidden=true;invalidateSource();};
 for(const field of [q('#paper-title'),q('#paper-author')])field.oninput=()=>{draft=null;q('.paper-analysis-result').hidden=true;controls();};
 q('#paper-prepare').onclick=async()=>{
  if(busy||(!selected&&!reference.value.trim()))return;if(reference.value&&!reference.reportValidity())return;
  busy=true;controls();draft=null;q('.paper-analysis-result').hidden=true;error.textContent='';status.textContent=selected?'正在上传你选择的 PDF…':'正在查找并下载 PDF…';
  try{
   await discard();let fileId=null;
   if(selected){if(selected.size>64*1024*1024)throw new Error('PDF 最大 64 MB');if(await selected.slice(0,5).text()!=='%PDF-')throw new Error('请选择有效的 PDF 文件');const form=new FormData();form.append('file',selected);const uploaded=await request('/api/files',{method:'POST',body:form});fileId=uploaded.id;owned.add(fileId);}
   const result=await post('/api/papers/prepare',{reference:reference.value.trim(),...(fileId?{file_id:fileId}:{})});if(closed)return;
   const source=result.source_url||reference.value.trim();q('.paper-source-links').hidden=!source;q('#paper-open-source').href=source;q('#paper-open-download').hidden=!result.download_url||result.download_url===source;q('#paper-open-download').href=result.download_url||source;
   if(result.status!=='ready'){prepared=null;status.textContent=result.message;status.classList.add('needs-input');return;}
   owned.add(result.file.id);status.textContent='正在读取所选 PDF…';const {extractPaperPDF}=await import('/static/vendor/pdf-extractor.mjs?v=20261028-paper-import');extracted=await extractPaperPDF(result.file.id);if(closed)return;
   prepared=result;const title=extracted.title.trim();q('#paper-title').value=(result.pdf_origin==='uploaded'?title||selected?.name.replace(/\.pdf$/i,''):result.paper.title||title)||result.file.name.replace(/\.pdf$/i,'');q('#paper-author').value=extracted.author||(result.pdf_origin==='downloaded'?(result.paper.authors||[]).join('; '):'');
   q('.paper-prepared').hidden=false;q('.paper-file-preview iframe').src='/static/pdf-viewer.html?file='+encodeURIComponent('/files/'+result.file.id+'?inline=1');q('.paper-selected-info').textContent=(result.pdf_origin==='uploaded'?'使用你上传的 PDF：':'使用自动下载的 PDF：')+result.file.name;
   status.classList.remove('needs-input');status.textContent=result.pdf_origin==='uploaded'?'已选用上传文件，链接仅保留为来源。':'PDF 已下载。请核对预览；如需换用自己的版本，可在上方重新上传。';
  }catch(e){prepared=null;extracted=null;q('.paper-prepared').hidden=true;error.textContent=e.message;status.textContent='';}
  finally{busy=false;controls();}
 };
 function payload(generate){return {file_id:prepared.file.id,reference:reference.value.trim(),title:q('#paper-title').value.trim(),author:q('#paper-author').value.trim(),year:prepared.pdf_origin==='downloaded'?prepared.paper.year||'':'',venue:prepared.pdf_origin==='downloaded'?prepared.paper.venue||'':'',text:extracted.text,page_count:extracted.page_count,pages_read:extracted.pages_read,truncated:extracted.truncated,generate};}
 q('#paper-generate').onclick=async()=>{
  if(busy||!prepared||!q('#paper-title').reportValidity())return;busy=true;draft=null;q('.paper-analysis-result').hidden=true;controls();error.textContent='';q('#paper-generate').textContent='正在分析所选 PDF…';
  try{draft=await post('/api/papers/draft',payload(true));if(closed)return;q('.paper-analysis-preview').innerHTML=window.WorkmoireEditor.render(draft.content);q('.paper-analysis-preview').querySelectorAll('iframe').forEach(el=>el.remove());q('.paper-analysis-result').hidden=false;q('.paper-analysis-result').scrollIntoView({block:'nearest'});}
  catch(e){draft=null;error.textContent=e.message;}
  finally{busy=false;q('#paper-generate').innerHTML=icon('spark')+'生成阅读档案';controls();}
 };
 q('#paper-use').onclick=async()=>{
  if(busy||!prepared||!q('#paper-title').reportValidity())return;busy=true;controls();error.textContent='';
  try{const result=draft||await post('/api/papers/draft',payload(false));if(closed)return;if(await onUse({...result,file:prepared.file})!==false){owned.delete(prepared.file.id);dialog.close();}}
  catch(e){error.textContent=e.message;}
  finally{busy=false;controls();}
 };
 q('.paper-close').onclick=()=>dialog.close();dialog.addEventListener('cancel',event=>{if(busy)event.preventDefault();});dialog.addEventListener('close',()=>{closed=true;q('.paper-file-preview iframe').removeAttribute('src');discard();dialog.remove();});dialog.addEventListener('click',event=>{if(event.target===dialog&&!busy){const r=dialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)dialog.close();}});
 dialog.showModal();controls();return dialog;
}
