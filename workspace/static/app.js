const labels={note:"知识库",project:"项目空间",paper:"论文大纲",log:"工作日志"};
const icons={note:"▤",project:"◈",paper:"▧",log:"◷"};
const statusLabels={inbox:"待整理",active:"进行中",done:"已完成",paused:"已暂停"};
const state={page:"dashboard",items:[],selected:null,stats:null,editorTab:"write",setup:false,assistant:null,draftTimer:null};
const $=sel=>document.querySelector(sel);
const $$=sel=>Array.from(document.querySelectorAll(sel));
const draftKey=kind=>"workmoire:draft:"+kind;
function readLocalDraft(kind){
  try{const raw=localStorage.getItem(draftKey(kind));return raw?JSON.parse(raw):null}catch(_){return null}
}
function clearLocalDraft(kind){try{localStorage.removeItem(draftKey(kind))}catch(_){} }
function scheduleLocalDraft(){
  if(!state.selected||state.selected.id||!$("#edit-title"))return;
  clearTimeout(state.draftTimer);
  state.draftTimer=setTimeout(()=>{try{localStorage.setItem(draftKey(state.page),JSON.stringify({...collectEditor(),saved_at:new Date().toISOString()}));$("#save-indicator").textContent="已保存在本机草稿"}catch(_){}},250);
}

function esc(value){
  return String(value??"").replace(/[&<>"']/g,ch=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
}
function formatDate(value,withTime=false){
  if(!value)return "";
  const d=new Date(value);
  if(Number.isNaN(d.getTime()))return value;
  return d.toLocaleDateString("zh-CN",{year:"numeric",month:"short",day:"numeric"})+(withTime?" "+d.toLocaleTimeString("zh-CN",{hour:"2-digit",minute:"2-digit"}):"");
}
function relativeDate(value){
  if(!value)return "";
  const then=new Date(value).getTime(),delta=Date.now()-then;
  if(delta<60000)return "刚刚";
  if(delta<3600000)return Math.floor(delta/60000)+" 分钟前";
  if(delta<86400000)return Math.floor(delta/3600000)+" 小时前";
  if(delta<604800000)return Math.floor(delta/86400000)+" 天前";
  return formatDate(value);
}
async function api(path,options={}){
  const headers=options.body instanceof FormData?{}:{"Content-Type":"application/json"};
  const response=await fetch(path,{credentials:"same-origin",...options,headers:{...headers,...(options.headers||{})}});
  let body={};
  try{body=await response.json()}catch(_){}
  if(!response.ok)throw new Error(body.error||"请求失败");
  return body;
}
function setVisible(id,visible){$(id).classList.toggle("is-hidden",!visible)}
function showApp(visible){setVisible("#auth-view",!visible);setVisible("#app-view",visible)}
function statusPill(status){return '<span class="status-pill '+esc(status)+'">'+esc(statusLabels[status]||status)+'</span>'}
function kindMark(kind){return '<span class="kind-mark '+esc(kind)+'">'+esc(icons[kind]||"·")+"</span>"}
function priorityMarkup(priority){return '<span class="priority" title="优先级 '+priority+'">'+[1,2,3].map(n=>'<i class="'+(n<=priority?"on":"")+'"></i>').join("")+"</span>"}
function parseMarkdown(source){
  let safe=esc(source||"");
  safe=safe.replace(/^### (.+)$/gm,"<h3>$1</h3>").replace(/^## (.+)$/gm,"<h2>$1</h2>").replace(/^# (.+)$/gm,"<h1>$1</h1>");
  safe=safe.replace(/^\- (.+)$/gm,"<li>$1</li>").replace(/(<li>.*<\/li>\n?)+/g,m=>"<ul>"+m+"</ul>");
  safe=safe.replace(/\*\*(.+?)\*\*/g,"<strong>$1</strong>").replace(/\`(.+?)\`/g,"<code>$1</code>");
  return safe.split(/\n{2,}/).map(block=>/^<(h|ul)/.test(block.trim())?block:"<p>"+block.replace(/\n/g,"<br>")+"</p>").join("");
}
function setAuthMode(setup,tokenRequired=false){
  state.setup=setup;
  $("#auth-title").textContent=setup?"创建你的工作空间":"欢迎回来";
  $("#auth-subtitle").textContent=setup?"设置唯一账号和密码，之后只有这个账号可以访问。":"把论文、项目和日常思路放在同一个安静的空间里。";
  $("#auth-submit").textContent=setup?"创建空间":"登录";
  $("#auth-confirm-row").classList.toggle("is-hidden",!setup);
  $("#auth-setup-token-row").classList.toggle("is-hidden",!setup||!tokenRequired);
  $("#auth-setup-token").required=setup&&tokenRequired;
  $("#auth-password").autocomplete=setup?"new-password":"current-password";
}
async function loadAssistantStatus(){try{state.assistant=await api("/api/assistant/status")}catch(_){state.assistant=null}}
async function boot(){
  try{
    const session=await api("/api/session");
    if(session.setup){showApp(false);setAuthMode(true,session.setup_token_required)}
    else if(session.authenticated){$("#account-name").textContent=session.username;$(".avatar").textContent=session.username.slice(0,1).toUpperCase();showApp(true);await loadAssistantStatus();await goPage("dashboard")}
    else{showApp(false);setAuthMode(false)}
  }catch(error){showApp(false);setAuthMode(false);$("#auth-error").textContent=error.message}
}
$("#auth-form").addEventListener("submit",async event=>{
  event.preventDefault();$("#auth-error").textContent="";
  const username=$("#auth-username").value.trim(),password=$("#auth-password").value;
  if(state.setup&&password!==$("#auth-confirm").value){$("#auth-error").textContent="两次密码不一致";return}
  try{
    const payload={username,password};if(state.setup&&!$("#auth-setup-token-row").classList.contains("is-hidden"))payload.setup_token=$("#auth-setup-token").value;
    const session=await api(state.setup?"/api/setup":"/api/login",{method:"POST",body:JSON.stringify(payload)});
    $("#account-name").textContent=session.username;$(".avatar").textContent=session.username.slice(0,1).toUpperCase();showApp(true);await loadAssistantStatus();await goPage("dashboard");
  }catch(error){$("#auth-error").textContent=error.message}
});
function editorHasChanges(){
  if(!state.selected||!$("#edit-title"))return false;
  const draft=collectEditor();
  return ["title","summary","content","tags","status","priority","due_date"].some(key=>String(draft[key]??"")!==String(state.selected[key]??""));
}
function confirmEditorLeave(){return !editorHasChanges()||window.confirm("当前内容尚未保存，确定离开吗？")}
async function goPage(page){
  if(state.page!==page&&!confirmEditorLeave())return;
  state.page=page;state.selected=null;state.editorTab="write";
  $$(".nav-item").forEach(item=>item.classList.toggle("is-active",item.dataset.page===page));
  $("#page-heading").textContent=page==="dashboard"?"总览":page==="files"?"文件空间":labels[page];
  if(page==="dashboard"){await loadStats();renderDashboard()}
  else if(page==="files"){await renderFiles()}
  else{await loadItems();renderContentPage()}
  $(".sidebar").classList.remove("is-open");
}
$(".nav-item").forEach(item=>item.onclick=()=>goPage(item.dataset.page));
async function loadStats(){state.stats=await api("/api/stats")}
async function loadItems(query=""){
  const params=new URLSearchParams({kind:state.page,limit:"500"});
  if(query)params.set("q",query);
  state.items=(await api("/api/items?"+params.toString())).items;
}
function renderDashboard(){
  const stats=state.stats||{counts:{},status_counts:{},recent:[],activity:[]};
  const count=k=>stats.counts[k]||0;
  const total=Object.values(stats.counts).reduce((a,b)=>a+b,0);
  const recent=stats.recent||[];
  const upcoming=stats.upcoming||[],activity=stats.activity||[];
  $("#page-content").innerHTML='<div class="page-title-row"><div><h1>总览</h1><p>把今天的想法放下来，再慢慢把它们组织成自己的系统。</p></div><div class="page-title-actions"><button class="button button-secondary" id="quick-log">记录今天</button><button class="button button-primary" id="quick-note">新建内容</button></div></div>'+
  '<div class="stats-grid"><div class="stat-card"><span class="stat-icon">◒</span><b>'+total+'</b><span>全部内容 <em>持续积累</em></span></div><div class="stat-card"><span class="stat-icon">▧</span><b>'+count("paper")+'</b><span>论文大纲</span></div><div class="stat-card"><span class="stat-icon">◈</span><b>'+count("project")+'</b><span>项目空间</span></div><div class="stat-card"><span class="stat-icon">◷</span><b>'+count("log")+'</b><span>工作日志</span></div></div>'+
  '<div class="section-label">工作流</div><div class="dashboard-columns"><section class="surface"><div class="surface-head"><h2>最近编辑</h2><a id="view-all">查看全部</a></div><div class="recent-list">'+(recent.length?recent.map(item=>'<div class="recent-item" data-id="'+item.id+'" data-kind="'+item.kind+'">'+kindMark(item.kind)+'<div class="recent-body"><div class="recent-title">'+esc(item.title)+'</div><div class="recent-meta">'+esc(labels[item.kind])+" · "+relativeDate(item.updated_at)+'</div></div>'+statusPill(item.status)+'</div>').join(""):'<div class="empty-state"><strong>还没有内容</strong><p>从一条知识卡片开始，给自己的思考留个位置。</p></div>')+'</div></section>'+
  '<section class="surface"><div class="surface-head"><h2>快速开始</h2></div><div class="quick-actions"><button class="quick-button" data-create-kind="note">'+kindMark("note")+'<span><strong>捕捉一个想法</strong><small>把还没成形的念头先记下来</small></span><span class="quick-plus">＋</span></button><button class="quick-button" data-create-kind="paper">'+kindMark("paper")+'<span><strong>搭一份论文大纲</strong><small>从问题、方法和实验开始</small></span><span class="quick-plus">＋</span></button><button class="quick-button" data-create-kind="project">'+kindMark("project")+'<span><strong>拆解一个项目</strong><small>明确目标、下一步和截止日期</small></span><span class="quick-plus">＋</span></button><button class="quick-button" data-create-kind="log">'+kindMark("log")+'<span><strong>写今天的工作日志</strong><small>留下过程，也留下进展</small></span><span class="quick-plus">＋</span></button></div></section></div>'+
  '<div class="dashboard-lower"><section class="surface"><div class="surface-head"><h2>截止日期</h2></div><div class="due-list">'+(upcoming.length?upcoming.map(item=>'<div class="due-item" data-id="'+item.id+'" data-kind="'+item.kind+'"><div class="due-date">'+esc(item.due_date)+'</div><div class="recent-body"><div class="recent-title">'+esc(item.title)+'</div><div class="recent-meta">'+esc(labels[item.kind])+'</div></div>'+statusPill(item.status)+'</div>').join(""):'<div class="empty-state"><strong>暂时没有截止日期</strong><p>在项目或论文中加上日期，下一步会出现在这里。</p></div>')+'</div></section><section class="surface"><div class="surface-head"><h2>最近活动</h2></div><div class="activity-list">'+(activity.length?activity.map(entry=>'<div class="activity-item"><span class="activity-dot"></span><div><div class="recent-title">'+esc(entry.label)+'</div><div class="recent-meta">'+esc(entry.created_at)+'</div></div></div>').join(""):'<div class="empty-state"><strong>还没有活动</strong><p>保存第一条内容后，这里会留下轨迹。</p></div>')+'</div></section></div>';
  $("#quick-note").onclick=()=>createItem("note");$("#quick-log").onclick=()=>createItem("log");
  $("#view-all").onclick=()=>goPage("note");
  $$(".quick-button").forEach(button=>button.onclick=()=>createItem(button.dataset.createKind));
  $$(".recent-item").forEach(row=>row.onclick=async()=>{await goPage(row.dataset.kind);state.selected=state.items.find(item=>String(item.id)===row.dataset.id);renderContentPage()});
  $$(".due-item").forEach(row=>row.onclick=async()=>{await goPage(row.dataset.kind);state.selected=state.items.find(item=>String(item.id)===row.dataset.id);renderContentPage()});
}
function defaultContent(kind){
  const templates={
    note:{title:"",summary:"",content:"",tags:"",status:"inbox",priority:2,due_date:""},
    project:{title:"",summary:"目标：\n下一步：\n",content:"## 背景\n\n## 目标\n\n## 下一步\n\n## 记录\n",tags:"",status:"active",priority:2,due_date:""},
    paper:{title:"",summary:"研究问题：",content:"# 论文大纲\n\n## 研究问题\n\n## 核心假设\n\n## 方法\n\n## 实验与验证\n\n## 预期贡献\n",tags:"",status:"inbox",priority:2,due_date:""},
    log:{title:formatDate(new Date().toISOString()),summary:"",content:"## 今天完成\n\n## 遇到的问题\n\n## 明天继续\n",tags:"日志",status:"active",priority:2,due_date:""}
  };
  return {...templates[kind],kind};
}
function createItem(kind){
  if(!confirmEditorLeave())return;
  state.page=kind;state.selected={id:null,...defaultContent(kind),...(readLocalDraft(kind)||{})};state.editorTab="write";$$(".nav-item").forEach(item=>item.classList.toggle("is-active",item.dataset.page===kind));$("#page-heading").textContent=labels[kind];loadItems().then(()=>renderContentPage()).catch(error=>{state.items=[];renderContentPage();window.alert(error.message)});
}
function renderContentPage(){
  const item=state.selected;
  $("#page-content").innerHTML='<div class="page-title-row"><div><h1>'+esc(labels[state.page])+'</h1><p>'+({note:"把碎片知识收拢起来，形成可以复用的脉络。",project:"让每一个项目都有清晰的目标和下一步。",paper:"从研究问题出发，把论文结构逐步搭起来。",log:"记录过程，让进展和思考可回看。"}[state.page])+'</p></div><div class="page-title-actions"><button class="button button-primary" id="new-content">新建'+esc(labels[state.page].replace("空间",""))+'</button></div></div>'+
  '<div class="content-layout"><section class="surface list-surface"><div class="list-toolbar"><div class="input-with-icon"><span>⌕</span><input id="list-search" class="control-input" placeholder="搜索当前空间"></div><select id="list-status" class="control-input"><option value="">全部状态</option><option value="inbox">待整理</option><option value="active">进行中</option><option value="done">已完成</option><option value="paused">已暂停</option></select></div><div id="item-list" class="item-list"></div></section><section id="editor" class="surface editor-surface"></section></div>';
  $("#new-content").onclick=()=>createItem(state.page);$("#list-search").oninput=drawItemList;$("#list-status").onchange=drawItemList;drawItemList();drawEditor();
}
function drawItemList(){
  const query=($("#list-search")?.value||"").toLowerCase(),status=$("#list-status")?.value||"";
  const items=state.items.filter(item=>(!status||item.status===status)&&(!query||(item.title+" "+item.summary+" "+item.tags+" "+item.content).toLowerCase().includes(query)));
  const box=$("#item-list");
  if(!items.length){box.innerHTML='<div class="empty-state"><strong>这里还没有内容</strong><p>点击右上角，先创建第一条。</p></div>';return}
  box.innerHTML=items.map(item=>'<div class="content-item '+(state.selected&&String(state.selected.id)===String(item.id)?"is-selected":"")+'" data-id="'+item.id+'"><div class="content-item-title">'+esc(item.title||"未命名")+'</div><div class="content-item-summary">'+esc(item.summary||"暂无摘要")+'</div><div class="content-item-meta">'+priorityMarkup(item.priority||2)+'<span>'+relativeDate(item.updated_at)+'</span><span class="spacer"></span>'+statusPill(item.status)+'</div></div>').join("");
  $$(".content-item").forEach(row=>row.onclick=()=>{if(!confirmEditorLeave())return;state.selected=state.items.find(item=>String(item.id)===row.dataset.id);state.editorTab="write";drawItemList();drawEditor()});
}
function drawEditor(){
  const editor=$("#editor");
  if(!state.selected){editor.innerHTML='<div class="editor-empty"><div><div class="empty-icon">✎</div><strong>选择一条内容开始整理</strong><p>也可以点击右上角新建一条。</p></div></div>';return}
  const item=state.selected;
  editor.innerHTML='<input id="edit-title" class="editor-title" placeholder="给这条内容起个标题" value="'+esc(item.title)+'"><input id="edit-summary" class="editor-summary" placeholder="用一句话概括它（可选）" value="'+esc(item.summary)+'"><div class="editor-grid"><div class="editor-body"><div class="editor-tabs"><button class="editor-tab '+(state.editorTab==="write"?"is-active":"")+'" data-tab="write">编辑</button><button class="editor-tab '+(state.editorTab==="preview"?"is-active":"")+'" data-tab="preview">预览</button></div><textarea id="edit-content" class="'+(state.editorTab==="preview"?"is-hidden":"")+'" placeholder="用 Markdown 写下你的思路……">'+esc(item.content)+'</textarea><div id="content-preview" class="preview-box '+(state.editorTab!=="preview"?"is-hidden":"")+'">'+parseMarkdown(item.content)+'</div></div><div class="editor-meta"><label class="form-field"><span>状态</span><select id="edit-status"><option value="inbox">待整理</option><option value="active">进行中</option><option value="done">已完成</option><option value="paused">已暂停</option></select></label><label class="form-field"><span>优先级</span><select id="edit-priority"><option value="1">低</option><option value="2">中</option><option value="3">高</option></select></label><label class="form-field"><span>截止日期</span><input id="edit-due" type="date" value="'+esc(item.due_date||"")+'"></label><label class="form-field"><span>标签</span><input id="edit-tags" placeholder="用逗号分隔" value="'+esc(item.tags||"")+'"></label></div></div><div class="editor-footer"><span id="save-indicator" class="save-indicator"></span><span class="spacer"></span><button id="delete-content" class="button button-danger">删除</button><button id="assistant-content" class="button button-secondary">整理建议</button><button id="save-content" class="button button-primary">保存内容</button></div>';
  $("#edit-status").value=item.status||"inbox";$("#edit-priority").value=String(item.priority||2);
  $$(".editor-tab").forEach(tab=>tab.onclick=()=>{collectEditorIntoState();state.editorTab=tab.dataset.tab;drawEditor()});
  $("#edit-content").oninput=()=>{if(state.editorTab==="preview"){$("#content-preview").innerHTML=parseMarkdown($("#edit-content").value)}};
  $("#save-content").onclick=saveItem;$("#delete-content").onclick=deleteItem;$("#assistant-content").onclick=openAssistant;
  $$("#editor input, #editor textarea, #editor select").forEach(field=>field.addEventListener("input",scheduleLocalDraft));
  $("#edit-title").focus();
}
function collectEditor(){
  return {kind:state.page,title:$("#edit-title").value.trim(),summary:$("#edit-summary").value.trim(),content:$("#edit-content").value,tags:$("#edit-tags").value,status:$("#edit-status").value,priority:Number($("#edit-priority").value),due_date:$("#edit-due").value};
}
function collectEditorIntoState(){
  if(!state.selected||!$("#edit-title"))return;
  Object.assign(state.selected,collectEditor());
}
function openAssistant(){
  if(!state.selected)return;
  collectEditorIntoState();
  const result=$("#assistant-result");
  result.classList.remove("is-error");
  result.textContent=state.assistant?.available?"选择整理方式后点击“开始整理”。":"服务器尚未配置本地 Codex。";
  $("#assistant-dialog").showModal();
}
async function runAssistant(){
  if(!state.selected)return;
  collectEditorIntoState();
  const result=$("#assistant-result");
  result.classList.remove("is-error");result.textContent="正在整理…";
  try{
    const data=await api("/api/assistant",{method:"POST",body:JSON.stringify({task:$("#assistant-task").value,title:state.selected.title,kind:state.page,content:state.selected.content})});
    result.textContent=data.result;
  }catch(error){result.textContent=error.message;result.classList.add("is-error")}
}

async function saveItem(){
  const data=collectEditor(),indicator=$("#save-indicator");
  if(!data.title){indicator.textContent="请先填写标题";return}
  indicator.textContent="保存中…";
  try{
    const result=state.selected.id?await api("/api/items/"+state.selected.id,{method:"PUT",body:JSON.stringify(data)}):await api("/api/items",{method:"POST",body:JSON.stringify(data)});
    state.selected=result.item;clearLocalDraft(state.page);await loadItems();drawItemList();drawEditor();$("#save-indicator").textContent="已保存 · "+new Date().toLocaleTimeString("zh-CN",{hour:"2-digit",minute:"2-digit"});
  }catch(error){indicator.textContent=error.message}
}
async function deleteItem(){
  if(!state.selected.id||!window.confirm("确定删除这条内容吗？删除后无法恢复。"))return;
  await api("/api/items/"+state.selected.id,{method:"DELETE"});state.selected=null;await loadItems();drawItemList();drawEditor()
}
async function renderFiles(){
  const data=await api("/api/files");
  $("#page-content").innerHTML='<div class="page-title-row"><div><h1>文件空间</h1><p>把论文、数据和项目资料放在一个可回看的位置。</p></div></div><section class="surface file-surface"><label id="upload-zone" class="upload-zone"><strong>拖拽文件到这里，或点击选择文件</strong><span>文件会保存在当前服务器的私有数据目录</span><small>单个文件最大 64 MB</small><input id="file-input" class="file-input" type="file"></label><div id="file-list" class="file-list"></div></section>';
  const zone=$("#upload-zone"),input=$("#file-input");input.onchange=()=>uploadFile(input.files[0]);["dragenter","dragover"].forEach(event=>zone.addEventListener(event,e=>{e.preventDefault();zone.classList.add("dragover")}));["dragleave","drop"].forEach(event=>zone.addEventListener(event,e=>{e.preventDefault();zone.classList.remove("dragover")}));zone.addEventListener("drop",e=>uploadFile(e.dataTransfer.files[0]));
  const list=$("#file-list");
  if(!data.files.length){list.innerHTML='<div class="empty-state"><strong>还没有文件</strong><p>上传第一份资料，让它和你的思路放在一起。</p></div>';return}
  list.innerHTML=data.files.map(file=>'<div class="file-row"><span class="file-symbol">↧</span><div><a href="/files/'+encodeURIComponent(file.id)+'" target="_blank">'+esc(file.name)+'</a><div class="file-size">'+formatBytes(file.size)+" · "+formatDate(file.created_at,true)+'</div></div><span class="spacer"></span><button class="file-delete" data-id="'+file.id+'" title="删除">×</button></div>').join("");
  $$(".file-delete").forEach(button=>button.onclick=async()=>{if(window.confirm("删除这个文件吗？")){await api("/api/files/"+button.dataset.id,{method:"DELETE"});renderFiles()}});
}
function formatBytes(bytes){if(bytes<1024)return bytes+" B";if(bytes<1024*1024)return (bytes/1024).toFixed(1)+" KB";return (bytes/1024/1024).toFixed(1)+" MB"}
async function uploadFile(file){
  if(!file)return;
  const form=new FormData();form.append("file",file);
  try{await api("/api/files",{method:"POST",body:form});await renderFiles()}catch(error){window.alert(error.message)}
}
$("#settings-button").onclick=()=>$("#settings-menu").classList.toggle("is-hidden");
$("#export-data").onclick=()=>{$("#settings-menu").classList.add("is-hidden");const link=document.createElement("a");link.href="/api/export";link.download="workmoire-export.json";document.body.appendChild(link);link.click();link.remove()};
$("#logout").onclick=async()=>{await api("/api/logout",{method:"POST"});showApp(false);setAuthMode(false)};
$("#change-password").onclick=()=>{$("#settings-menu").classList.add("is-hidden");$("#password-message").textContent="";$("#password-dialog").showModal()};
$("#password-form").addEventListener("submit",async event=>{if(event.submitter?.value==="cancel")return;event.preventDefault();$("#password-message").textContent="";try{await api("/api/password",{method:"POST",body:JSON.stringify({old_password:$("#old-password").value,new_password:$("#new-password").value})});$("#password-message").textContent="密码已更新";setTimeout(()=>$("#password-dialog").close(),500)}catch(error){$("#password-message").textContent=error.message}});
$("#assistant-close").onclick=()=>$("#assistant-dialog").close();$("#assistant-run").onclick=runAssistant;
$("#global-search-trigger").onclick=()=>{$("#search-dialog").showModal();$("#global-search").focus()};
$("#global-search").oninput=async()=>{const query=$("#global-search").value.trim(),box=$("#search-results");if(!query){box.innerHTML='<div class="search-empty">输入关键词开始搜索</div>';return}const result=await api("/api/items?q="+encodeURIComponent(query)+"&limit=30");box.innerHTML=result.items.length?result.items.map(item=>'<div class="search-result" data-id="'+item.id+'" data-kind="'+item.kind+'">'+kindMark(item.kind)+'<div><strong>'+esc(item.title)+'</strong><div class="recent-meta">'+esc(labels[item.kind])+" · "+esc(item.summary||"暂无摘要")+'</div></div></div>').join(""):'<div class="search-empty">没有找到匹配内容</div>';$$("#search-results .search-result").forEach(row=>row.onclick=async()=>{$("#search-dialog").close();await goPage(row.dataset.kind);state.selected=state.items.find(item=>String(item.id)===row.dataset.id);renderContentPage()})};
document.addEventListener("keydown",event=>{if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==="k"){event.preventDefault();$("#search-dialog").showModal();$("#global-search").focus()}if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==="s"&&state.selected){event.preventDefault();saveItem()}if(event.key==="Escape"){$("#settings-menu")?.classList.add("is-hidden")}});
$("#mobile-menu").onclick=()=>$(".sidebar").classList.toggle("is-open");
boot();
