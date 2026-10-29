import {progressPanel,uploadFile,trackPaperJob} from './operation-progress.js';
import {tagColor} from './tag-colors.js';
const icon=name=>window.WorkmoireIcons.render(name);

export function openPaperImport({request,post,assistantAvailable,onUse}){
 const dialog=document.createElement('dialog');dialog.className='dialog paper-import-dialog';dialog.setAttribute('aria-label','新建论文资料');
 const card=document.createElement('div');card.className='dialog-card paper-import-card';
 card.innerHTML='<div class="dialog-head"><h2>新建论文资料</h2><button type="button" class="icon-button paper-close" aria-label="关闭论文导入">'+icon('close')+'</button></div><div class="paper-import-scroll"><p class="dialog-note">上传 PDF 后可整理发表情况、作者团队与研究领域。来源链接可不填，不会自动下载。</p><label class="paper-upload-zone"><span>'+icon('upload')+'上传 PDF</span><small>选择本地文件，最大 64 MB</small><input id="paper-pdf-input" type="file" accept="application/pdf,.pdf" aria-label="选择论文 PDF"></label><div class="paper-selected-upload" hidden><span></span><button type="button" class="quiet-button" id="paper-clear-upload">移除选择</button></div><label class="field"><span>来源链接（可选）</span><input id="paper-reference" type="url" placeholder="https://…" aria-label="论文链接" maxlength="3000"></label><button id="paper-prepare" type="button" class="button secondary">上传并读取 PDF</button><div class="paper-import-status" role="status"></div><div class="paper-transfer-progress"></div><div class="paper-extraction-progress"></div><div class="paper-source-links" hidden><a id="paper-open-source" class="quiet-button" target="_blank" rel="noopener noreferrer">打开原文</a></div><section class="paper-prepared" hidden><label class="field"><span>论文标题</span><input id="paper-title" maxlength="200" aria-label="论文标题" required></label><label class="field"><span>作者（可选）</span><input id="paper-author" maxlength="300" aria-label="论文作者"></label><div class="paper-selected-info"></div><details class="paper-file-preview" open><summary>核对所选 PDF</summary><iframe title="所选论文 PDF 预览"></iframe></details><div class="paper-analysis-actions"><button id="paper-generate" type="button" class="button secondary">'+icon('spark')+'AI 分析论文</button><span class="paper-text-status quiet"></span></div><div class="paper-ai-progress"></div></section><p class="paper-import-error error" role="alert"></p><section class="paper-analysis-result" hidden><div class="section-label">论文档案预览</div><div class="paper-field-tags" role="group" aria-label="随文档保存的领域标签"></div><div class="prose paper-analysis-preview"></div></section></div><div class="dialog-actions"><button id="paper-use" type="button" class="button primary" disabled>放入编辑器</button></div>';
 card.insertBefore(card.querySelector('.paper-ai-progress'),card.querySelector('.dialog-actions'));
 dialog.append(card);document.body.append(dialog);const q=selector=>card.querySelector(selector),reference=q('#paper-reference'),fileInput=q('#paper-pdf-input'),status=q('.paper-import-status'),error=q('.paper-import-error');
 let titleConfirmed=false,authorConfirmed=false;let selected=null,prepared=null,extracted=null,draft=null,busy=false,closed=false,sourceVersion=0;const transfer=progressPanel(q(".paper-transfer-progress"),"上传 PDF"),extraction=progressPanel(q(".paper-extraction-progress"),"提取 PDF 文字"),analysis=progressPanel(q(".paper-ai-progress"),"AI 分析论文");const owned=new Set();
 async function discard(ids=[...owned]){for(const id of ids){try{await request('/api/files/'+id,{method:'DELETE'});owned.delete(id);}catch{/* Leave recoverable, unassociated files in attachment management if cleanup fails. */}}}
 function controls(){
  q('.paper-close').disabled=busy;reference.disabled=busy;fileInput.disabled=busy;q('#paper-clear-upload').disabled=busy;q('#paper-prepare').disabled=busy||!selected;
  q('#paper-title').disabled=busy;q('#paper-author').disabled=busy;q('.paper-field-tags').querySelectorAll('input').forEach(input=>input.disabled=busy);
  q('#paper-use').disabled=busy||!prepared||!q('#paper-title').value.trim();
  const readable=(extracted?.text||'').replace(/\[第 \d+ 页\]/g,'').trim().length>=80;
  q('#paper-generate').disabled=busy||!prepared||!readable||!assistantAvailable;
  q('.paper-text-status').textContent=!prepared?'':!readable?'未提取到足够文字，可先建立资料并手动阅读。':!assistantAvailable?'当前未配置整理助手，可先建立资料。':(extracted.truncated?'已提取部分文字':'已提取文字')+' · '+extracted.pages_read+' / '+extracted.page_count+' 页';
 }
 function invalidateSource(){titleConfirmed=false;authorConfirmed=false;sourceVersion++;transfer.reset();extraction.reset();analysis.reset();prepared=null;extracted=null;draft=null;q('.paper-prepared').hidden=true;q('.paper-analysis-result').hidden=true;q('.paper-source-links').hidden=true;q('.paper-file-preview iframe').removeAttribute('src');status.textContent='';error.textContent='';controls();}
 reference.oninput=()=>{const source=reference.value.trim(),valid=source.startsWith('https://')&&reference.validity.valid;q('.paper-source-links').hidden=!valid;if(valid)q('#paper-open-source').href=source;};
 fileInput.onchange=()=>{selected=fileInput.files[0]||null;invalidateSource();q('.paper-selected-upload').hidden=!selected;q('.paper-selected-upload span').textContent=selected?selected.name:'';};
 q('#paper-clear-upload').onclick=()=>{selected=null;fileInput.value='';q('.paper-selected-upload').hidden=true;invalidateSource();};
 q('#paper-title').oninput=()=>{titleConfirmed=true;controls();};q('#paper-author').oninput=()=>{authorConfirmed=true;controls();};
 q('#paper-prepare').onclick=async()=>{
  if(busy||!selected)return;if(reference.value&&!reference.reportValidity())return;
  busy=true;controls();draft=null;q('.paper-analysis-result').hidden=true;error.textContent='';status.textContent='';transfer.reset();extraction.reset();analysis.reset();const version=++sourceVersion,fileForImport=selected;let localText=null,uploadedSuccessfully=false;
  try{
   await discard();
   if(selected.size>64*1024*1024)throw new Error('PDF 最大 64 MB');if(await selected.slice(0,5).text()!=='%PDF-')throw new Error('请选择有效的 PDF 文件');
   extraction.stage('读取本地 PDF','pdf-open',2);
   localText=import('/static/vendor/pdf-extractor.mjs?v=20261029-manual-pdf').then(({extractPaperPDF})=>extractPaperPDF(fileForImport,{onProgress:event=>{if(version===sourceVersion&&!closed&&event.stage==='extracting')extraction.pages(event.done,event.total);}})).then(value=>{if(version===sourceVersion&&!closed)extraction.done(value.truncated?'提取完成（部分文字）':'文字读取完成');return {value};},error=>({error}));
   transfer.stage('准备上传 PDF','',1);const uploaded=await uploadFile(fileForImport,{onProgress:event=>transfer.transfer(event),onTransferComplete:()=>transfer.stage('文件已发送，等待服务器确认','upload-ack',2)});owned.add(uploaded.id);uploadedSuccessfully=true;transfer.done('PDF 上传完成');
   const result=await post('/api/papers/prepare',{reference:reference.value.trim(),file_id:uploaded.id});if(closed)return;
   const source=result.source_url||reference.value.trim();q('.paper-source-links').hidden=!source;q('#paper-open-source').href=source;
   if(result.status!=='ready')throw new Error(result.message||'请手动上传 PDF');
   owned.add(result.file.id);
   const resultText=await localText;if(resultText.error)throw resultText.error;extracted=resultText.value;if(closed)return;
   prepared=result;q('#paper-title').value=extracted.title.trim()||fileForImport.name.replace(/\.pdf$/i,'');q('#paper-author').value=extracted.author||'';
   q('.paper-prepared').hidden=false;q('.paper-file-preview iframe').src='/static/pdf-viewer.html?file='+encodeURIComponent('/files/'+result.file.id+'?inline=1');q('.paper-selected-info').textContent='使用你上传的 PDF：'+result.file.name;
   status.textContent='已上传，请核对 PDF 预览和论文信息。';
  }catch(e){sourceVersion++;prepared=null;extracted=null;q('.paper-prepared').hidden=true;error.textContent=e.message;status.textContent='';if(!uploadedSuccessfully)transfer.fail('PDF 上传未完成');extraction.fail('文字读取未完成');}
  finally{busy=false;controls();}
 };
 function renderTags(tags){const root=q('.paper-field-tags');root.replaceChildren();if(!tags.length){root.textContent='未确定领域，可在文档目录中手动添加标签。';return;}const label=document.createElement('span');label.textContent='领域标签';root.append(label);for(const tag of tags.slice(0,2)){const row=document.createElement('label'),check=document.createElement('input'),badge=document.createElement('span');row.className='paper-field-tag';check.type='checkbox';check.value=tag;check.checked=true;check.setAttribute('aria-label','保存领域标签 '+tag);badge.className='bookmark-tag';badge.dataset.tagColor=tagColor(tag);badge.textContent=tag;row.append(check,badge);root.append(row);}}
 function payload(generate){return {file_id:prepared.file.id,reference:reference.value.trim(),title:q('#paper-title').value.trim(),author:q('#paper-author').value.trim(),title_confirmed:titleConfirmed,author_confirmed:authorConfirmed,text:extracted.text,page_count:extracted.page_count,pages_read:extracted.pages_read,truncated:extracted.truncated,generate};}
 q('#paper-generate').onclick=async()=>{
  if(busy||!prepared||!q('#paper-title').reportValidity())return;busy=true;draft=null;q('.paper-analysis-result').hidden=true;controls();error.textContent='';q('#paper-generate').textContent='正在分析所选 PDF…';analysis.reset();analysis.stage('正在提交分析请求','',1);
  try{const job=await post('/api/papers/draft',{...payload(true),background:true});draft=job.job_id?await trackPaperJob(job,request,analysis,()=>!closed):job;if(!job.job_id)analysis.done('论文分析完成');if(closed)return;if(!titleConfirmed&&draft.title)q('#paper-title').value=draft.title;if(!authorConfirmed&&draft.paper?.authors?.length)q('#paper-author').value=draft.paper.authors.join('; ');renderTags(draft.tags||[]);q('.paper-analysis-preview').innerHTML=window.WorkmoireEditor.render(draft.analysis||draft.content);q('.paper-analysis-preview').querySelectorAll('iframe').forEach(el=>el.remove());q('.paper-analysis-result').hidden=false;q('.paper-analysis-result').scrollIntoView({block:'nearest'});}
  catch(e){draft=null;analysis.fail('论文分析未完成');error.textContent=e.message;}
  finally{busy=false;q('#paper-generate').innerHTML=icon('spark')+'AI 分析论文';controls();}
 };
 q('#paper-use').onclick=async()=>{
  if(busy||!prepared||!q('#paper-title').reportValidity())return;busy=true;controls();error.textContent='';
  try{if(reference.value&&!reference.reportValidity())return;const result=draft?.details?await post('/api/papers/draft',{...payload(false),reviewed_analysis:draft.details,selected_tags:[...q('.paper-field-tags').querySelectorAll('input:checked')].map(el=>el.value)}):draft||await post('/api/papers/draft',payload(false));if(closed)return;if(await onUse({...result,file:prepared.file})!==false){owned.delete(prepared.file.id);dialog.close();}}
  catch(e){error.textContent=e.message;}
  finally{busy=false;controls();}
 };
 q('.paper-close').onclick=()=>dialog.close();dialog.addEventListener('cancel',event=>{if(busy)event.preventDefault();});dialog.addEventListener('close',()=>{closed=true;sourceVersion++;transfer.destroy();extraction.destroy();analysis.destroy();q('.paper-file-preview iframe').removeAttribute('src');discard();dialog.remove();});dialog.addEventListener('click',event=>{if(event.target===dialog&&!busy){const r=dialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)dialog.close();}});
 dialog.showModal();controls();request('/api/papers/timing').then(data=>{if(!closed)q('#paper-generate').title='通常约 '+Math.ceil(data.estimate.low)+'–'+Math.ceil(data.estimate.high)+' 秒，实际时间随材料和服务负载变化';}).catch(()=>{});return dialog;
}
