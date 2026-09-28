const labels={note:"知识库",project:"项目空间",paper:"论文大纲",log:"工作日志",review:"今日复盘",calendar:"计划日历",trash:"回收站"};
const icons={note:"▤",project:"◈",paper:"▧",log:"◷",review:"✦",calendar:"▦",trash:"♲"};
const statusLabels={inbox:"待整理",active:"进行中",done:"已完成",paused:"已暂停"};
const state={page:"dashboard",items:[],allItems:[],selected:null,savedSnapshot:null,stats:null,reviewData:null,calendarDate:new Date(),editorTab:"write",listTag:"",listSort:"updated",fileSearch:"",fileSearchTimer:null,fileSearchController:null,focusMode:false,setup:false,authenticated:false,assistant:null,assistantResult:"",draftTimer:null,captureDraftTimer:null,searchController:null};
const captureDraftKey="workmoire:capture-draft";
const $=sel=>document.querySelector(sel);
const $$=sel=>Array.from(document.querySelectorAll(sel));
const draftKey=(kind,id=null)=>"workmoire:draft:"+kind+":"+(id==null?"new":id);
function readLocalDraft(kind,id=null){
  try{const raw=localStorage.getItem(draftKey(kind,id));return raw?JSON.parse(raw):null}catch(_){return null}
}
function clearLocalDraft(kind,id=null){try{localStorage.removeItem(draftKey(kind,id))}catch(_){} }
function scheduleLocalDraft(){
  if(!state.selected||!$("#edit-title"))return;
  clearTimeout(state.draftTimer);
  state.draftTimer=setTimeout(()=>{try{localStorage.setItem(draftKey(state.page,state.selected.id||null),JSON.stringify({...collectEditor(),item_id:state.selected.id||null,base_updated_at:state.selected.updated_at||"",saved_at:new Date().toISOString()}));$("#save-indicator").textContent="已保存在本机草稿"}catch(_){}},250);
}
function editorSnapshot(item){
  if(!item)return null;
  return ["kind","title","summary","content","tags","status","priority","due_date","parent_id","pinned"].reduce((snapshot,key)=>{snapshot[key]=key==="pinned"?Boolean(item[key]):item[key]??"";return snapshot},{});
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
function formatDueDate(value){
  const parts=String(value||"").split("-");
  return parts.length===3?parts[0]+"年"+Number(parts[1])+"月"+Number(parts[2])+"日":value||"";
}
async function refreshServiceStatus(){
  const dot=$(".server-status i"),label=$("#server-status-label");
  if(!dot||!label)return;
  try{
    const response=await fetch("/healthz",{credentials:"same-origin",cache:"no-store"});
    if(!response.ok)throw new Error("health check failed");
    dot.classList.remove("is-offline");label.textContent="本地服务在线";
  }catch(_){
    dot.classList.add("is-offline");label.textContent="服务连接异常";
  }
}
async function api(path,options={}){
  const headers=options.body instanceof FormData?{}:{"Content-Type":"application/json"};
  const response=await fetch(path,{credentials:"same-origin",...options,headers:{...headers,...(options.headers||{})}});
  let body={};
  try{body=await response.json()}catch(_){}
  if(response.status===401&&state.authenticated){
    state.authenticated=false;showApp(false);setAuthMode(false);$("#auth-error").textContent="登录已失效，请重新登录";
  }
  if(!response.ok)throw new Error(body.error||"请求失败");
  return body;
}
function setVisible(id,visible){$(id).classList.toggle("is-hidden",!visible)}
function showApp(visible){setVisible("#auth-view",!visible);setVisible("#app-view",visible)}
function statusPill(status){return '<span class="status-pill '+esc(status)+'">'+esc(statusLabels[status]||status)+'</span>'}
function kindMark(kind){return '<span class="kind-mark '+esc(kind)+'">'+esc(icons[kind]||"·")+"</span>"}
function priorityMarkup(priority){return '<span class="priority" title="优先级 '+priority+'">'+[1,2,3].map(n=>'<i class="'+(n<=priority?"on":"")+'"></i>').join("")+"</span>"}
function dueItemMarkup(item){const overdue=Boolean(item.overdue);return '<div class="due-item '+(overdue?"is-overdue":"")+'" data-id="'+item.id+'" data-kind="'+item.kind+'"><div class="due-date">'+(overdue?"已逾期 · ":"")+esc(formatDueDate(item.due_date))+'</div><div class="recent-body"><div class="recent-title">'+esc(item.title)+'</div><div class="recent-meta">'+esc(labels[item.kind])+'</div></div>'+statusPill(item.status)+'<button class="due-complete" data-id="'+item.id+'" type="button">完成</button></div>'}
async function completeDueItem(event){
  event.stopPropagation();
  const itemId=event.currentTarget.dataset.id;
  const item=[...(state.stats?.overdue||[]),...(state.stats?.upcoming||[])].find(candidate=>String(candidate.id)===itemId);
  if(!item)return;
  const button=event.currentTarget;button.disabled=true;button.textContent="更新中…";
  try{
    await api("/api/items/"+item.id,{method:"PUT",body:JSON.stringify({kind:item.kind,title:item.title,summary:item.summary,content:item.content,tags:item.tags,status:"done",priority:item.priority,due_date:item.due_date,parent_id:item.parent_id,pinned:Boolean(item.pinned)})});
    await loadStats();renderDashboard();
  }catch(error){button.disabled=false;button.textContent="完成";window.alert(error.message)}
}
function inboxItemMarkup(item){return '<div class="inbox-item" data-id="'+item.id+'" data-kind="'+item.kind+'">'+kindMark(item.kind)+'<div class="recent-body"><div class="recent-title">'+esc(item.title||"未命名")+'</div><div class="recent-meta">'+esc(labels[item.kind])+' · '+esc(item.summary||"等待整理")+'</div></div>'+priorityMarkup(item.priority||2)+'<button class="inbox-start" data-id="'+item.id+'" type="button">开始整理</button></div>'}
async function promoteInboxItem(event){
  event.stopPropagation();
  const itemId=event.currentTarget.dataset.id,item=(state.stats?.inbox||[]).find(candidate=>String(candidate.id)===itemId);
  if(!item)return;
  const button=event.currentTarget;button.disabled=true;button.textContent="更新中…";
  try{
    await api("/api/items/"+item.id,{method:"PUT",body:JSON.stringify({kind:item.kind,title:item.title,summary:item.summary,content:item.content,tags:item.tags,status:"active",priority:item.priority,due_date:item.due_date,parent_id:item.parent_id,pinned:Boolean(item.pinned)})});
    await loadStats();renderDashboard();
  }catch(error){button.disabled=false;button.textContent="开始整理";window.alert(error.message)}
}
function parseMarkdown(source){
  let safe=esc(source||"");
  safe=safe.replace(/^### (.+)$/gm,"<h3>$1</h3>").replace(/^## (.+)$/gm,"<h2>$1</h2>").replace(/^# (.+)$/gm,"<h1>$1</h1>");
  safe=safe.replace(/^\- \[([ xX])\] (.+)$/gm,(_,mark,text)=>'<li class="task-item"><input type="checkbox" disabled '+(mark.toLowerCase()==="x"?"checked":"")+'><span>'+text+'</span></li>');
  safe=safe.replace(/^\- (.+)$/gm,"<li>$1</li>").replace(/((?:<li(?: [^>]*)?>.*<\/li>\n?)+)/g,m=>"<ul>"+m+"</ul>");
  safe=safe.replace(/\*\*(.+?)\*\*/g,"<strong>$1</strong>").replace(/\`(.+?)\`/g,"<code>$1</code>");
  safe=safe.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,'<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
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
function openCapture(){
  if(!state.authenticated)return;
  $("#capture-title").value="";$("#capture-content").value="";$("#capture-error").textContent="";$("#capture-submit").disabled=false;$("#capture-submit").textContent="放入待整理箱";
  let draft=null;try{draft=JSON.parse(localStorage.getItem(captureDraftKey)||"null")}catch(_){draft=null}
  $("#capture-draft-notice").classList.toggle("is-hidden",!draft||(!draft.title&&!draft.content));
  $("#capture-dialog").showModal();$("#capture-title").focus();
}
function scheduleCaptureDraft(){
  clearTimeout(state.captureDraftTimer);
  state.captureDraftTimer=setTimeout(()=>{const title=$("#capture-title").value,content=$("#capture-content").value;try{if(!title&&!content){localStorage.removeItem(captureDraftKey);return}localStorage.setItem(captureDraftKey,JSON.stringify({title,content,saved_at:new Date().toISOString()}))}catch(_){}} ,250);
}
function restoreCaptureDraft(){
  try{const draft=JSON.parse(localStorage.getItem(captureDraftKey)||"null");if(!draft)return;$("#capture-title").value=draft.title||"";$("#capture-content").value=draft.content||"";$("#capture-draft-notice").classList.add("is-hidden");$("#capture-title").focus()}catch(_){}
}
function discardCaptureDraft(){try{localStorage.removeItem(captureDraftKey)}catch(_){}$("#capture-draft-notice").classList.add("is-hidden")}
async function saveCapture(event){
  if(event.submitter?.value==="cancel")return;
  event.preventDefault();
  const title=$("#capture-title").value.trim(),content=$("#capture-content").value;
  if(!title){$("#capture-error").textContent="请先写一个标题";return}
  const button=$("#capture-submit");button.disabled=true;button.textContent="保存中…";$("#capture-error").textContent="";
  try{
    await api("/api/items",{method:"POST",body:JSON.stringify({kind:"note",title,summary:"",content,tags:"",status:"inbox",priority:2,due_date:"",parent_id:null,pinned:false})});
    try{localStorage.removeItem(captureDraftKey)}catch(_){}
    $("#capture-dialog").close();
    if(state.page==="dashboard"){await loadStats();renderDashboard()}
  }catch(error){button.disabled=false;button.textContent="放入待整理箱";$("#capture-error").textContent=error.message}
}
async function loadAssistantStatus(){try{state.assistant=await api("/api/assistant/status")}catch(_){state.assistant=null}}
async function boot(){
  try{
    const session=await api("/api/session");
    if(session.setup){showApp(false);setAuthMode(true,session.setup_token_required)}
    else if(session.authenticated){state.authenticated=true;$("#account-name").textContent=session.username;$(".avatar").textContent=session.username.slice(0,1).toUpperCase();showApp(true);await loadAssistantStatus();await goPage("dashboard")}
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
    state.authenticated=true;$("#account-name").textContent=session.username;$(".avatar").textContent=session.username.slice(0,1).toUpperCase();showApp(true);await loadAssistantStatus();await goPage("dashboard");
  }catch(error){$("#auth-error").textContent=error.message}
});
function editorHasChanges(){
  if(!state.selected||!$("#edit-title"))return false;
  const draft=collectEditor();
  const baseline=state.savedSnapshot||editorSnapshot(state.selected)||{};
  return ["kind","title","summary","content","tags","status","priority","due_date","parent_id","pinned"].some(key=>String(draft[key]??"")!==String(baseline[key]??""));
}
function confirmEditorLeave(){return !editorHasChanges()||window.confirm("当前内容尚未保存，确定离开吗？")}
async function goPage(page){
  if(!confirmEditorLeave())return false;
  state.page=page;state.selected=null;state.savedSnapshot=null;state.listTag="";state.listSort="updated";state.editorTab="write";state.focusMode=false;document.body.classList.remove("editor-focus-mode");
  $$(".nav-item").forEach(item=>item.classList.toggle("is-active",item.dataset.page===page));
  $("#page-heading").textContent=page==="dashboard"?"总览":page==="files"?"文件空间":labels[page];
  if(page==="dashboard"){await loadStats();renderDashboard()}
  else if(page==="review"){await renderReview()}
  else if(page==="calendar"){await renderCalendar()}
  else if(page==="files"){await renderFiles()}
  else if(page==="trash"){await renderTrash()}
  else{await loadItems();renderContentPage()}
  $(".sidebar").classList.remove("is-open");
  return true;
}
$$(".nav-item").forEach(item=>item.onclick=()=>goPage(item.dataset.page));
async function loadStats(){state.stats=await api("/api/stats")}
async function loadItems(query=""){
  const params=new URLSearchParams({kind:state.page,limit:"500"});
  if(query)params.set("q",query);
  state.items=(await api("/api/items?"+params.toString())).items;
  if(!query)state.allItems=(await api("/api/items?limit=500")).items;
}
function renderDashboard(){
  const stats=state.stats||{counts:{},status_counts:{},recent:[],activity:[]};
  const count=k=>stats.counts[k]||0;
  const total=Object.values(stats.counts).reduce((a,b)=>a+b,0);
  const recent=stats.recent||[];
  const inbox=stats.inbox||[],pinned=stats.pinned||[],upcoming=stats.upcoming||[],overdue=stats.overdue||[],activity=stats.activity||[];
  const dueItems=overdue.map(item=>({...item,overdue:true})).concat(upcoming);
  $("#page-content").innerHTML='<div class="page-title-row"><div><h1>总览</h1><p>把今天的想法放下来，再慢慢把它们组织成自己的系统。</p></div><div class="page-title-actions"><button class="button button-secondary" id="quick-review">今日复盘</button><button class="button button-secondary" id="quick-log">记录今天</button><button class="button button-primary" id="quick-note">新建内容</button></div></div>'+
  '<div class="stats-grid"><div class="stat-card"><span class="stat-icon">◒</span><b>'+total+'</b><span>全部内容 <em>持续积累</em></span></div><div class="stat-card"><span class="stat-icon">▧</span><b>'+count("paper")+'</b><span>论文大纲</span></div><div class="stat-card"><span class="stat-icon">◈</span><b>'+count("project")+'</b><span>项目空间</span></div><div class="stat-card"><span class="stat-icon">◷</span><b>'+count("log")+'</b><span>工作日志</span></div></div>'+
  '<div class="section-label">工作流</div><div class="dashboard-columns"><section class="surface"><div class="surface-head"><h2>最近编辑</h2><a id="view-all">查看全部</a></div><div class="recent-list">'+(recent.length?recent.map(item=>'<div class="recent-item" data-id="'+item.id+'" data-kind="'+item.kind+'">'+kindMark(item.kind)+'<div class="recent-body"><div class="recent-title">'+esc(item.title)+'</div><div class="recent-meta">'+esc(labels[item.kind])+" · "+relativeDate(item.updated_at)+'</div></div>'+statusPill(item.status)+'</div>').join(""):'<div class="empty-state"><strong>还没有内容</strong><p>从一条知识卡片开始，给自己的思考留个位置。</p></div>')+'</div></section>'+
  '<section class="surface"><div class="surface-head"><h2>快速开始</h2></div><div class="quick-actions"><button class="quick-button" data-create-kind="note">'+kindMark("note")+'<span><strong>捕捉一个想法</strong><small>把还没成形的念头先记下来</small></span><span class="quick-plus">＋</span></button><button class="quick-button" data-create-kind="paper">'+kindMark("paper")+'<span><strong>搭一份论文大纲</strong><small>从问题、方法和实验开始</small></span><span class="quick-plus">＋</span></button><button class="quick-button" data-create-kind="project">'+kindMark("project")+'<span><strong>拆解一个项目</strong><small>明确目标、下一步和截止日期</small></span><span class="quick-plus">＋</span></button><button class="quick-button" data-create-kind="log">'+kindMark("log")+'<span><strong>写今天的工作日志</strong><small>留下过程，也留下进展</small></span><span class="quick-plus">＋</span></button></div></section></div>'+
  '<div class="dashboard-lower"><section class="surface"><div class="surface-head"><h2>置顶内容</h2></div><div class="pinned-list">'+(pinned.length?pinned.map(item=>'<div class="pinned-item" data-id="'+item.id+'" data-kind="'+item.kind+'">'+kindMark(item.kind)+'<div class="recent-body"><div class="recent-title">'+esc(item.title)+'</div><div class="recent-meta">'+esc(labels[item.kind])+' · '+relativeDate(item.updated_at)+'</div></div><span class="pin-mark">★</span></div>').join(""):'<div class="empty-state"><strong>还没有置顶内容</strong><p>把正在推进的项目或重要知识置顶，它们会一直出现在这里。</p></div>')+'</div></section><section class="surface"><div class="surface-head"><h2>下一步期限</h2></div><div class="due-list">'+(dueItems.length?dueItems.map(dueItemMarkup).join(""):'<div class="empty-state"><strong>暂时没有待处理的截止日期</strong><p>在项目或论文中加上日期，下一步会出现在这里。</p></div>')+'</div></section></div><div class="dashboard-lower"><section class="surface"><div class="surface-head"><h2>待整理</h2><span class="surface-count">'+inbox.length+'</span></div><div class="inbox-list">'+(inbox.length?inbox.map(inboxItemMarkup).join(""):'<div class="empty-state"><strong>待整理箱是空的</strong><p>捕捉到的想法会先停在这里。</p></div>')+'</div></section><section class="surface"><div class="surface-head"><h2>最近活动</h2></div><div class="activity-list">'+(activity.length?activity.map(entry=>'<div class="activity-item '+(entry.target_type==="item"||entry.target_type==="file"?"is-clickable":"")+'" data-target-type="'+esc(entry.target_type||"")+'" data-target-id="'+esc(entry.target_id||"")+'" title="'+(entry.target_type==="item"||entry.target_type==="file"?"打开关联内容":"")+'"><span class="activity-dot"></span><div><div class="recent-title">'+esc(entry.label)+'</div><div class="recent-meta">'+esc(formatDate(entry.created_at,true))+'</div></div></div>').join(""):'<div class="empty-state"><strong>还没有活动</strong><p>保存第一条内容后，这里会留下轨迹。</p></div>')+'</div></section></div>';
  $("#quick-note").onclick=openCapture;$("#quick-log").onclick=openTodayLog;$("#quick-review").onclick=()=>goPage("review");
  $("#view-all").onclick=()=>goPage("note");
  $$(".quick-button").forEach(button=>button.onclick=()=>button.dataset.createKind==="note"?openCapture():button.dataset.createKind==="log"?openTodayLog():createItem(button.dataset.createKind));
  $$(".recent-item,.due-item,.pinned-item,.inbox-item").forEach(row=>row.onclick=async()=>{if(!await goPage(row.dataset.kind))return;state.selected=state.items.find(item=>String(item.id)===row.dataset.id);state.savedSnapshot=editorSnapshot(state.selected);renderContentPage()});
  $$(".inbox-start").forEach(button=>button.onclick=promoteInboxItem);
  $$(".due-complete").forEach(button=>button.onclick=completeDueItem);
  $$(".activity-item.is-clickable").forEach(row=>row.onclick=openActivity);
}
function reviewItemMarkup(item){
  const start=item.status==="inbox"?'<button class="review-promote" data-review-id="'+item.id+'" type="button">开始整理</button>':'';
  return '<div class="review-row" data-review-id="'+item.id+'" data-review-kind="'+item.kind+'">'+kindMark(item.kind)+'<div class="recent-body"><div class="recent-title">'+esc(item.title||"未命名")+'</div><div class="recent-meta">'+esc(labels[item.kind])+' · '+(item.due_date?esc(formatDueDate(item.due_date)):esc(relativeDate(item.updated_at)))+'</div></div>'+priorityMarkup(item.priority||2)+'<div class="review-row-actions"><button class="review-open" data-review-id="'+item.id+'" type="button">打开</button>'+start+'<button class="review-done" data-review-id="'+item.id+'" type="button">完成</button></div></div>';
}
function reviewItemById(itemId){
  const groups=state.reviewData||{};
  return ["inbox","overdue","today","stale"].flatMap(key=>groups[key]||[]).find(item=>String(item.id)===String(itemId));
}
async function openReviewItem(event){
  event.stopPropagation();
  const itemId=event.currentTarget.dataset.reviewId;
  try{
    const result=await api("/api/items/"+encodeURIComponent(itemId));
    if(!await goPage(result.item.kind))return;
    state.selected=state.items.find(item=>String(item.id)===String(itemId))||result.item;state.savedSnapshot=editorSnapshot(state.selected);renderContentPage();
  }catch(error){window.alert(error.message)}
}
async function updateReviewStatus(event,status){
  event.stopPropagation();
  const button=event.currentTarget,item=reviewItemById(button.dataset.reviewId);
  if(!item)return;
  button.disabled=true;button.textContent="更新中…";
  try{
    await api("/api/items/"+item.id,{method:"PUT",body:JSON.stringify({kind:item.kind,title:item.title,summary:item.summary,content:item.content,tags:item.tags,status,priority:item.priority,due_date:item.due_date,parent_id:item.parent_id,pinned:Boolean(item.pinned)})});
    await renderReview();
  }catch(error){button.disabled=false;button.textContent=status==="done"?"完成":"开始整理";window.alert(error.message)}
}
async function renderReview(){
  state.reviewData=await api("/api/review");
  const data=state.reviewData,total=["inbox","overdue","today","stale"].reduce((sum,key)=>sum+(data[key]||[]).length,0);
  const section=(key,title,hint,empty)=>'<section class="surface review-section"><div class="surface-head"><div><h2>'+title+'</h2><p class="review-hint">'+hint+'</p></div><span class="surface-count">'+(data[key]||[]).length+'</span></div><div class="review-list">'+((data[key]||[]).length?(data[key]||[]).map(reviewItemMarkup).join(""):'<div class="empty-state review-empty"><strong>'+empty+'</strong></div>')+'</div></section>';
  $("#page-content").innerHTML='<div class="page-title-row"><div><h1>今日复盘</h1><p>先处理最需要你注意的内容，再回到深度工作。</p></div><div class="page-title-actions"><button id="review-refresh" class="button button-secondary">刷新队列</button></div></div><div class="review-summary"><div><span class="review-summary-label">今天建议处理</span><strong>'+total+'</strong><span>项</span></div><p>完成或开始整理后，队列会自动更新。</p></div><div class="review-grid">'+section("overdue","已逾期","先处理已经错过日期的事项。","没有逾期内容")+section("today","今天到期","今天需要给出明确结果的内容。","今天没有到期内容")+section("inbox","待整理","把捕捉到的碎片变成下一步。","待整理箱是空的")+section("stale","很久没更新","超过 7 天没有推进、且没有截止日期的进行中内容。","没有长期停滞内容")+'</div>';
  $("#review-refresh").onclick=renderReview;
  $$(".review-open").forEach(button=>button.onclick=openReviewItem);
  $$(".review-done").forEach(button=>button.onclick=event=>updateReviewStatus(event,"done"));
  $$(".review-promote").forEach(button=>button.onclick=event=>updateReviewStatus(event,"active"));
  $$(".review-row").forEach(row=>row.onclick=openReviewItem);
}
function calendarDateKey(year,month,day){return year+"-"+String(month+1).padStart(2,"0")+"-"+String(day).padStart(2,"0")}
async function openCalendarItem(event){
  event.stopPropagation();
  try{
    const result=await api("/api/items/"+encodeURIComponent(event.currentTarget.dataset.id));
    if(!await goPage(result.item.kind))return;
    state.selected=state.items.find(item=>String(item.id)===String(result.item.id))||result.item;state.savedSnapshot=editorSnapshot(state.selected);renderContentPage();
  }catch(error){window.alert(error.message)}
}
async function renderCalendar(){
  const year=state.calendarDate.getFullYear(),month=state.calendarDate.getMonth();
  const data=await api("/api/calendar?year="+year+"&month="+(month+1));
  const items=data.items||[],byDay={};items.forEach(item=>{(byDay[item.due_date] ||= []).push(item)});
  const firstDay=new Date(year,month,1),offset=(firstDay.getDay()+6)%7,days=new Date(year,month+1,0).getDate(),cellCount=Math.ceil((offset+days)/7)*7;
  const today=new Date(),todayKey=calendarDateKey(today.getFullYear(),today.getMonth(),today.getDate());
  const weekdayLabels=["一","二","三","四","五","六","日"];
  let cells="";
  for(let index=0;index<cellCount;index++){
    const day=index-offset+1,inside=day>=1&&day<=days,key=inside?calendarDateKey(year,month,day):"";
    const dayItems=inside?(byDay[key]||[]):[];
    cells+='<div class="calendar-cell '+(inside?"":"is-muted")+(key===todayKey?" is-today":"")+'">'+(inside?'<div class="calendar-day-number">'+day+'</div>':'')+(dayItems.length?'<div class="calendar-items">'+dayItems.slice(0,4).map(item=>'<button class="calendar-item '+esc(item.status||"")+'" data-id="'+item.id+'" data-kind="'+item.kind+'" title="'+esc(item.title)+'"><span class="calendar-item-mark '+esc(item.kind)+'"></span><span>'+esc(item.title||"未命名")+'</span></button>').join("")+(dayItems.length>4?'<span class="calendar-more">还有 '+(dayItems.length-4)+' 项</span>':"")+'</div>':"")+'</div>';
  }
  const doneCount=items.filter(item=>item.status==="done").length;
  $("#page-content").innerHTML='<div class="page-title-row"><div><h1>计划日历</h1><p>把项目、论文和工作日志的截止日期放到同一条时间线上。</p></div><div class="page-title-actions"><button id="calendar-today" class="button button-secondary">回到今天</button></div></div><section class="surface calendar-surface"><div class="calendar-toolbar"><button id="calendar-prev" class="icon-button" aria-label="上个月">‹</button><h2>'+year+'年'+(month+1)+'月</h2><button id="calendar-next" class="icon-button" aria-label="下个月">›</button><span class="spacer"></span><span class="calendar-summary">'+items.length+' 项安排 · '+doneCount+' 项已完成</span></div><div class="calendar-weekdays">'+weekdayLabels.map(day=>'<span>'+day+'</span>').join("")+'</div><div class="calendar-grid">'+cells+'</div></section>';
  $("#calendar-prev").onclick=()=>{state.calendarDate=new Date(year,month-1,1);renderCalendar()};
  $("#calendar-next").onclick=()=>{state.calendarDate=new Date(year,month+1,1);renderCalendar()};
  $("#calendar-today").onclick=()=>{state.calendarDate=new Date();renderCalendar()};
  $$(".calendar-item").forEach(button=>button.onclick=openCalendarItem);
}
async function openActivity(event){
  const row=event.currentTarget,type=row.dataset.targetType,id=row.dataset.targetId;
  if(!id)return;
  if(type==="file"){window.open("/files/"+encodeURIComponent(id),"_blank","noopener");return}
  if(type!=="item")return;
  try{
    const result=await api("/api/items/"+encodeURIComponent(id));
    if(!await goPage(result.item.kind))return;
    state.selected=state.items.find(item=>String(item.id)===String(id));state.savedSnapshot=editorSnapshot(state.selected);renderContentPage();
  }catch(_){row.title="这条内容已移入回收站或不存在"}
}
function defaultContent(kind){
  const templates={
    note:{title:"",summary:"",content:"",tags:"",status:"inbox",priority:2,due_date:"",parent_id:null,pinned:false},
    project:{title:"",summary:"目标：\n下一步：\n",content:"## 背景\n\n## 目标\n\n## 下一步\n\n## 记录\n",tags:"",status:"active",priority:2,due_date:"",parent_id:null,pinned:false},
    paper:{title:"",summary:"研究问题：",content:"# 论文大纲\n\n## 研究问题\n\n## 核心假设\n\n## 方法\n\n## 实验与验证\n\n## 预期贡献\n",tags:"",status:"inbox",priority:2,due_date:"",parent_id:null,pinned:false},
    log:{title:formatDate(new Date().toISOString()),summary:"",content:"## 今天完成\n\n## 遇到的问题\n\n## 明天继续\n",tags:"日志",status:"active",priority:2,due_date:"",parent_id:null,pinned:false}
  };
  return {...templates[kind],kind};
}
function createItem(kind){
  if(!confirmEditorLeave())return;
  state.page=kind;state.listTag="";state.listSort="updated";state.focusMode=false;document.body.classList.remove("editor-focus-mode");state.selected={id:null,...defaultContent(kind),...(readLocalDraft(kind)||{})};state.savedSnapshot=editorSnapshot(state.selected);state.editorTab="write";$$(".nav-item").forEach(item=>item.classList.toggle("is-active",item.dataset.page===kind));$("#page-heading").textContent=labels[kind];loadItems().then(()=>renderContentPage()).catch(error=>{state.items=[];renderContentPage();window.alert(error.message)});
}
async function openTodayLog(){
  const title=formatDate(new Date().toISOString());
  try{
    const result=await api("/api/items?kind=log&limit=50");
    const existing=(result.items||[]).find(item=>item.title===title);
    if(!existing){createItem("log");return}
    if(!await goPage("log"))return;
    state.selected=state.items.find(item=>String(item.id)===String(existing.id));
    state.savedSnapshot=editorSnapshot(state.selected);renderContentPage();
  }catch(error){window.alert(error.message)}
}
function renderContentPage(){
  const item=state.selected;
  $("#page-content").innerHTML='<div class="page-title-row"><div><h1>'+esc(labels[state.page])+'</h1><p>'+({note:"把碎片知识收拢起来，形成可以复用的脉络。",project:"让每一个项目都有清晰的目标和下一步。",paper:"从研究问题出发，把论文结构逐步搭起来。",log:"记录过程，让进展和思考可回看。"}[state.page])+'</p></div><div class="page-title-actions"><button class="button button-primary" id="new-content">新建'+esc(labels[state.page].replace("空间",""))+'</button></div></div>'+
  '<div class="content-layout"><section class="surface list-surface"><div class="list-toolbar"><div class="input-with-icon"><span>⌕</span><input id="list-search" class="control-input" placeholder="搜索当前空间"></div><select id="list-status" class="control-input"><option value="">全部状态</option><option value="inbox">待整理</option><option value="active">进行中</option><option value="done">已完成</option><option value="paused">已暂停</option></select><select id="list-sort" class="control-input" aria-label="排序"><option value="updated">最近更新</option><option value="priority">优先级最高</option><option value="due">截止日期</option><option value="title">标题</option></select><div id="list-tags" class="tag-filter" aria-label="标签筛选"></div></div><div id="item-list" class="item-list"></div></section><section id="editor" class="surface editor-surface"></section></div>';
  $("#new-content").onclick=()=>createItem(state.page);$("#list-search").oninput=drawItemList;$("#list-status").onchange=drawItemList;$("#list-sort").onchange=drawItemList;drawItemList();drawEditor();
}
async function renderTrash(){
  const data=await api("/api/trash");
  const items=data.items||[],files=data.files||[];
  $("#page-content").innerHTML='<div class="page-title-row"><div><h1>回收站</h1><p>误删的内容会暂时保留在这里，恢复后会回到原来的工作空间。</p></div></div><div class="trash-grid"><section class="surface"><div class="surface-head"><h2>内容</h2><span class="surface-count">'+items.length+'</span></div><div id="trash-items" class="trash-list"></div></section><section class="surface"><div class="surface-head"><h2>文件</h2><span class="surface-count">'+files.length+'</span></div><div id="trash-files" class="trash-list"></div></section></div>';
  const itemBox=$("#trash-items"),fileBox=$("#trash-files");
  itemBox.innerHTML=items.length?items.map(item=>'<div class="trash-row"><div class="trash-row-body">'+kindMark(item.kind)+'<div class="recent-body"><div class="recent-title">'+esc(item.title)+'</div><div class="recent-meta">'+esc(labels[item.kind])+' · 删除于 '+formatDate(item.deleted_at,true)+'</div></div></div><div class="trash-actions"><button class="button button-secondary restore-item" data-id="'+item.id+'">恢复</button><button class="button button-danger purge-item" data-id="'+item.id+'">永久删除</button></div></div>').join(""):'<div class="empty-state"><strong>回收站是空的</strong><p>最近删除的内容会在这里暂存。</p></div>';
  fileBox.innerHTML=files.length?files.map(file=>'<div class="trash-row"><div class="trash-row-body"><span class="file-symbol">↧</span><div class="recent-body"><div class="recent-title">'+esc(file.name)+'</div><div class="recent-meta">'+formatBytes(file.size)+' · 删除于 '+formatDate(file.deleted_at,true)+'</div></div></div><div class="trash-actions"><button class="button button-secondary restore-file" data-id="'+esc(file.id)+'">恢复</button><button class="button button-danger purge-file" data-id="'+esc(file.id)+'">永久删除</button></div></div>').join(""):'<div class="empty-state"><strong>没有已删除文件</strong><p>上传文件后，删除的附件会在这里暂存。</p></div>';
  $$(".restore-item").forEach(button=>button.onclick=async()=>{await api("/api/trash/items/"+button.dataset.id+"/restore",{method:"POST"});await renderTrash()});
  $$(".purge-item").forEach(button=>button.onclick=async()=>{if(window.confirm("永久删除后无法恢复，确定继续吗？")){await api("/api/trash/items/"+button.dataset.id,{method:"DELETE"});await renderTrash()}});
  $$(".restore-file").forEach(button=>button.onclick=async()=>{await api("/api/trash/files/"+encodeURIComponent(button.dataset.id)+"/restore",{method:"POST"});await renderTrash()});
  $$(".purge-file").forEach(button=>button.onclick=async()=>{if(window.confirm("永久删除后无法恢复，确定继续吗？")){await api("/api/trash/files/"+encodeURIComponent(button.dataset.id),{method:"DELETE"});await renderTrash()}});
}
function drawItemList(){
  const query=$("#list-search")?.value.toLowerCase()||"",status=$("#list-status")?.value||"",sort=$("#list-sort")?.value||state.listSort;state.listSort=sort;
  drawTagFilter();
  const items=state.items.filter(item=>(!status||item.status===status)&&(!state.listTag||item.tags_list?.includes(state.listTag)||item.tags?.split(",").includes(state.listTag))&&(!query||(item.title+" "+item.summary+" "+item.tags+" "+item.content).toLowerCase().includes(query))).sort((a,b)=>compareItems(a,b,sort));
  const box=$("#item-list");
  if(!items.length){box.innerHTML='<div class="empty-state"><strong>这里还没有内容</strong><p>点击右上角，先创建第一条。</p></div>';return}
  box.innerHTML=items.map(item=>'<div class="content-item '+(state.selected&&String(state.selected.id)===String(item.id)?"is-selected":"")+'" data-id="'+item.id+'"><div class="content-item-head"><div class="content-item-title">'+esc(item.title||"未命名")+'</div><button class="pin-toggle '+(item.pinned?"is-pinned":"")+'" data-id="'+item.id+'" title="'+(item.pinned?"取消置顶":"置顶内容")+'" aria-label="'+(item.pinned?"取消置顶":"置顶内容")+'">★</button></div><div class="content-item-summary">'+esc(item.summary||"暂无摘要")+'</div><div class="content-item-meta">'+priorityMarkup(item.priority||2)+'<span>'+relativeDate(item.updated_at)+'</span><span class="spacer"></span>'+statusPill(item.status)+'</div></div>').join("");
  $$(".content-item").forEach(row=>row.onclick=()=>{if(!confirmEditorLeave())return;state.selected=state.items.find(item=>String(item.id)===row.dataset.id);state.savedSnapshot=editorSnapshot(state.selected);state.editorTab="write";drawItemList();drawEditor()});
  $$(".pin-toggle").forEach(button=>button.onclick=async event=>{event.stopPropagation();if(!confirmEditorLeave())return;const item=state.items.find(candidate=>String(candidate.id)===button.dataset.id);if(!item)return;try{const result=await api("/api/items/"+item.id+"/pin",{method:"POST",body:JSON.stringify({pinned:!item.pinned})});Object.assign(item,result.item);const all=state.allItems.find(candidate=>String(candidate.id)===button.dataset.id);if(all)Object.assign(all,result.item);if(state.selected&&String(state.selected.id)===button.dataset.id){Object.assign(state.selected,result.item);state.savedSnapshot=editorSnapshot(result.item);drawEditor()}drawItemList()}catch(error){window.alert(error.message)}});
}
function compareItems(a,b,sort){
  const updated=(b.updated_at||"").localeCompare(a.updated_at||"");
  if(sort==="priority")return Number(b.priority||0)-Number(a.priority||0)||updated;
  if(sort==="due")return (a.due_date||"9999-12-31").localeCompare(b.due_date||"9999-12-31")||updated;
  if(sort==="title")return String(a.title||"").localeCompare(String(b.title||""),"zh-CN")||updated;
  return Number(b.pinned||0)-Number(a.pinned||0)||updated;
}
function drawTagFilter(){
  const box=$("#list-tags");
  if(!box)return;
  const counts={};state.items.forEach(item=>(item.tags_list||String(item.tags||"").split(",").filter(Boolean)).forEach(tag=>{counts[tag]=(counts[tag]||0)+1}));
  const tags=Object.keys(counts).sort((a,b)=>counts[b]-counts[a]||a.localeCompare(b)).slice(0,18);
  box.innerHTML=tags.length?'<button class="tag-chip '+(!state.listTag?"is-active":"")+'" data-tag="">全部</button>'+tags.map(tag=>'<button class="tag-chip '+(state.listTag===tag?"is-active":"")+'" data-tag="'+esc(tag)+'">'+esc(tag)+' <small>'+counts[tag]+'</small></button>').join(""):'';
  $$(".tag-chip").forEach(button=>button.onclick=()=>{state.listTag=button.dataset.tag;drawItemList()});
}
function relatedTargetOptions(item){
  const excluded=new Set([String(item.id)]);
  return (state.allItems.length?state.allItems:state.items).filter(candidate=>!excluded.has(String(candidate.id))).map(candidate=>'<option value="'+candidate.id+'">'+esc((labels[candidate.kind]||"内容")+" · "+(candidate.title||"未命名"))+'</option>').join("");
}
async function renderRelatedItems(itemId){
  const list=$("#related-list");
  if(!list)return;
  try{
    const result=await api("/api/items/"+encodeURIComponent(itemId)+"/links");
    if(!state.selected||String(state.selected.id)!==String(itemId)||$("#related-list")!==list)return;
    const items=result.items||[];
    const linkedIds=new Set(items.map(item=>String(item.id)));
    $$("#related-target option").forEach(option=>{option.disabled=linkedIds.has(option.value)});
    list.innerHTML=items.length?items.map(item=>'<div class="related-row"><button class="related-link" data-related-id="'+item.id+'" data-related-kind="'+item.kind+'">'+kindMark(item.kind)+'<span>'+esc(item.title||"未命名")+'</span></button><button class="related-remove" data-related-id="'+item.id+'" title="解除关联" aria-label="解除与 '+esc(item.title||"未命名")+' 的关联">×</button></div>').join(""):'<span class="related-empty">还没有横向关联</span>';
    $$("#related-list .related-remove").forEach(button=>button.onclick=async event=>{event.stopPropagation();button.disabled=true;try{await api("/api/items/"+encodeURIComponent(itemId)+"/links/"+encodeURIComponent(button.dataset.relatedId),{method:"DELETE"});await renderRelatedItems(itemId)}catch(error){button.disabled=false;window.alert(error.message)}});
    $$("#related-list .related-link").forEach(link=>link.onclick=async()=>{
      try{
        const result=await api("/api/items/"+encodeURIComponent(link.dataset.relatedId));
        if(!await goPage(result.item.kind))return;
        state.selected={...result.item};state.savedSnapshot=editorSnapshot(state.selected);renderContentPage();
      }catch(error){window.alert(error.message)}
    });
  }catch(error){if($("#related-list")===list)list.innerHTML='<span class="related-empty">关联列表暂时不可用</span>'}
}
async function addRelatedItem(){
  const select=$("#related-target"),button=$("#add-related");
  if(!select||!button||!select.value||!state.selected?.id)return;
  const itemId=state.selected.id;
  button.disabled=true;
  try{
    await api("/api/items/"+encodeURIComponent(itemId)+"/links",{method:"POST",body:JSON.stringify({target_id:Number(select.value)})});
    select.value="";
    if(state.selected?.id===itemId&&$("#related-target")===select)await renderRelatedItems(itemId);
  }catch(error){window.alert(error.message)}
  finally{if($("#add-related")===button)button.disabled=false}
}
function drawEditor(){
  const editor=$("#editor");
  if(!state.selected){editor.innerHTML='<div class="editor-empty"><div><div class="empty-icon">✎</div><strong>选择一条内容开始整理</strong><p>也可以点击右上角新建一条。</p></div></div>';return}
  const item=state.selected;
  const localDraft=item.id?readLocalDraft(state.page,item.id):null;
  const draftAvailable=Boolean(localDraft&&String(localDraft.base_updated_at||"")===String(item.updated_at||""));
  const draftNotice=draftAvailable?'<div class="draft-notice" id="draft-notice"><span>发现这条内容的本机未保存草稿</span><button id="restore-draft" class="button button-secondary">恢复草稿</button><button id="dismiss-draft" class="draft-dismiss">忽略</button></div>':'';
  const kindOptions=["note","project","paper","log"].map(kind=>'<option value="'+kind+'">'+labels[kind]+'</option>').join("");
  const parentOptions=(state.allItems.length?state.allItems:state.items).filter(candidate=>String(candidate.id)!==String(item.id)).map(candidate=>'<option value="'+candidate.id+'">'+esc((labels[candidate.kind]||"内容")+" · "+(candidate.title||"未命名"))+'</option>').join("");
  const parentItem=item.parent_id!=null?state.allItems.find(candidate=>String(candidate.id)===String(item.parent_id)):null;
  const childItems=item.id?state.allItems.filter(candidate=>String(candidate.parent_id)===String(item.id)):[];
  const hierarchyMarkup=(parentItem||childItems.length)?'<section class="relation-panel"><div class="relation-heading">层级关系</div>'+(parentItem?'<div class="relation-group"><span class="relation-label">上级</span><button class="related-link" data-related-id="'+parentItem.id+'" data-related-kind="'+parentItem.kind+'">'+kindMark(parentItem.kind)+'<span>'+esc(parentItem.title)+'</span></button></div>':'')+(childItems.length?'<div class="relation-group"><span class="relation-label">下级</span><div class="relation-children">'+childItems.map(child=>'<button class="related-link" data-related-id="'+child.id+'" data-related-kind="'+child.kind+'">'+kindMark(child.kind)+'<span>'+esc(child.title)+'</span></button>').join('')+'</div></div>':'')+'</section>':'';
  const relatedMarkup=item.id?'<section class="relation-panel related-content-panel"><div class="relation-heading">横向关联 · 更改即时保存</div><div id="related-list" class="related-list"><span class="related-empty">加载中…</span></div><div class="related-add"><select id="related-target" class="control-input" aria-label="要关联的内容"><option value="">选择要关联的内容…</option>'+relatedTargetOptions(item)+'</select><button id="add-related" class="button button-secondary" type="button">关联</button></div></section>':'';
  const relationMarkup=hierarchyMarkup+relatedMarkup;
  const attachmentMarkup=item.id?'<section class="attachment-panel"><div class="attachment-head"><div><strong>关联文件</strong><small>只显示属于这条内容的附件</small></div><label class="button button-secondary attachment-upload">上传文件<input id="item-file-input" class="file-input" type="file"></label></div><div id="item-file-list" class="item-file-list"></div></section>':'<section class="attachment-panel attachment-empty"><strong>关联文件</strong><span>保存内容后可以上传论文、数据或项目资料。</span></section>';
  editor.innerHTML=draftNotice+'<input id="edit-title" class="editor-title" placeholder="给这条内容起个标题" value="'+esc(item.title)+'"><input id="edit-summary" class="editor-summary" placeholder="用一句话概括它（可选）" value="'+esc(item.summary)+'"><div class="editor-grid"><div class="editor-body"><div class="editor-tabs"><button class="editor-tab '+(state.editorTab==="write"?"is-active":"")+'" data-tab="write">编辑</button><button class="editor-tab '+(state.editorTab==="preview"?"is-active":"")+'" data-tab="preview">预览</button></div><textarea id="edit-content" class="'+(state.editorTab==="preview"?"is-hidden":"")+'" placeholder="用 Markdown 写下你的思路……">'+esc(item.content)+'</textarea><div id="content-preview" class="preview-box '+(state.editorTab!=="preview"?"is-hidden":"")+'">'+parseMarkdown(item.content)+'</div></div><div class="editor-meta"><label class="form-field"><span>内容类型</span><select id="edit-kind">'+kindOptions+'</select></label><label class="form-field"><span>状态</span><select id="edit-status"><option value="inbox">待整理</option><option value="active">进行中</option><option value="done">已完成</option><option value="paused">已暂停</option></select></label><label class="form-field"><span>优先级</span><select id="edit-priority"><option value="1">低</option><option value="2">中</option><option value="3">高</option></select></label><label class="form-field"><span>截止日期</span><input id="edit-due" type="date" value="'+esc(item.due_date||"")+'"></label><label class="form-field"><span>标签</span><input id="edit-tags" placeholder="用逗号分隔" value="'+esc(item.tags||"")+'"></label><label class="form-field"><span>上级内容</span><select id="edit-parent"><option value="">无上级内容</option>'+parentOptions+'</select></label><label class="form-check"><input id="edit-pinned" type="checkbox" '+(item.pinned?"checked":"")+'><span>置顶内容</span></label></div></div>'+relationMarkup+attachmentMarkup+'<div class="editor-footer"><span id="save-indicator" class="save-indicator"></span><span class="spacer"></span>'+'<button id="focus-mode" class="button button-secondary">'+(state.focusMode?"退出专注":"专注模式")+'</button>'+(item.id?'<button id="duplicate-content" class="button button-secondary">另存副本</button>':"")+'<button id="delete-content" class="button button-danger">删除</button><button id="assistant-content" class="button button-secondary">整理建议</button><button id="save-content" class="button button-primary">保存内容</button></div>';
  $("#edit-kind").value=item.kind||state.page;$("#edit-status").value=item.status||"inbox";$("#edit-priority").value=String(item.priority||2);$("#edit-parent").value=item.parent_id==null?"":String(item.parent_id);
  $$(".editor-tab").forEach(tab=>tab.onclick=()=>{collectEditorIntoState();state.editorTab=tab.dataset.tab;drawEditor()});
  $("#edit-content").oninput=()=>{if(state.editorTab==="preview"){$("#content-preview").innerHTML=parseMarkdown($("#edit-content").value)}};
  $("#save-content").onclick=saveItem;$("#delete-content").onclick=deleteItem;$("#focus-mode").onclick=toggleFocusMode;if($("#duplicate-content"))$("#duplicate-content").onclick=duplicateItem;$("#assistant-content").onclick=openAssistant;$("#assistant-content").disabled=!state.assistant?.available;if($("#assistant-content").disabled)$("#assistant-content").title="服务器尚未配置本地 Codex";if($("#add-related"))$("#add-related").onclick=addRelatedItem;
  $$("#editor input, #editor textarea, #editor select").forEach(field=>field.addEventListener("input",scheduleLocalDraft));
  if(draftAvailable){
    $("#restore-draft").onclick=()=>{Object.assign(state.selected,localDraft);clearLocalDraft(state.page,state.selected.id);drawEditor();$("#save-indicator").textContent="草稿已恢复，请保存内容"};
    $("#dismiss-draft").onclick=()=>{clearLocalDraft(state.page,state.selected.id);drawEditor()};
  }
  $$(".related-link").forEach(link=>link.onclick=async()=>{if(!await goPage(link.dataset.relatedKind))return;state.selected=state.items.find(candidate=>String(candidate.id)===link.dataset.relatedId);state.savedSnapshot=editorSnapshot(state.selected);renderContentPage()});
  if(item.id){renderItemFiles(item.id);renderRelatedItems(item.id)}
  $("#edit-title").focus();
}
function collectEditor(){
  return {kind:$("#edit-kind").value,title:$("#edit-title").value.trim(),summary:$("#edit-summary").value.trim(),content:$("#edit-content").value,tags:$("#edit-tags").value,status:$("#edit-status").value,priority:Number($("#edit-priority").value),due_date:$("#edit-due").value,parent_id:$("#edit-parent").value?Number($("#edit-parent").value):null,pinned:$("#edit-pinned").checked};
}
function collectEditorIntoState(){
  if(!state.selected||!$("#edit-title"))return;
  Object.assign(state.selected,collectEditor());
}
function duplicateItem(){
  if(!state.selected?.id)return;
  collectEditorIntoState();
  const source=state.selected;
  state.selected={...source,id:null,title:(source.title||"未命名")+" · 副本",status:"inbox",due_date:"",pinned:false,created_at:"",updated_at:"",deleted_at:""};
  state.savedSnapshot=editorSnapshot(state.selected);state.editorTab="write";clearLocalDraft(state.page,null);drawItemList();drawEditor();$("#save-indicator").textContent="副本已创建，保存后写入知识库";
}
function toggleFocusMode(){
  collectEditorIntoState();
  state.focusMode=!state.focusMode;document.body.classList.toggle("editor-focus-mode",state.focusMode);drawEditor();
  if($("#edit-content"))$("#edit-content").focus();
}
function openAssistant(){
  if(!state.selected)return;
  collectEditorIntoState();
  const result=$("#assistant-result");
  state.assistantResult="";
  result.classList.remove("is-error");
  result.textContent=state.assistant?.available?"选择整理方式后点击“开始整理”。":"服务器尚未配置本地 Codex。";
  $("#assistant-apply-summary").classList.add("is-hidden");$("#assistant-apply-content").classList.add("is-hidden");
  $("#assistant-dialog").showModal();
}
async function runAssistant(){
  if(!state.selected)return;
  collectEditorIntoState();
  const result=$("#assistant-result");
  const runButton=$("#assistant-run");runButton.disabled=true;runButton.textContent="整理中…";result.classList.remove("is-error");result.textContent="正在整理…";
  try{
    const data=await api("/api/assistant",{method:"POST",body:JSON.stringify({task:$("#assistant-task").value,title:state.selected.title,kind:state.selected.kind||state.page,summary:state.selected.summary,tags:state.selected.tags,content:state.selected.content})});
    state.assistantResult=data.result;result.textContent=data.result;$("#assistant-apply-summary").classList.remove("is-hidden");$("#assistant-apply-content").classList.remove("is-hidden");
  }catch(error){result.textContent=error.message;result.classList.add("is-error")}
  finally{runButton.disabled=false;runButton.textContent="再次整理"}
}
function applyAssistantResult(target){
  if(!state.selected||!state.assistantResult)return;
  if(target==="content"){
    const current=$("#edit-content").value.trim();
    state.selected.content=current?current+"\n\n"+state.assistantResult:state.assistantResult;
  }else{
    state.selected.summary=state.assistantResult.trim().slice(0,500);
  }
  $("#assistant-dialog").close();drawEditor();scheduleLocalDraft();$("#save-indicator").textContent="助手结果已加入未保存修改";
}

async function saveItem(){
  const data=collectEditor(),indicator=$("#save-indicator");
  if(!data.title){indicator.textContent="请先填写标题";return}
  const button=$("#save-content");button.disabled=true;indicator.textContent="保存中…";
  try{
    const previousKind=state.page,result=state.selected.id?await api("/api/items/"+state.selected.id,{method:"PUT",body:JSON.stringify(data)}):await api("/api/items",{method:"POST",body:JSON.stringify(data)});
    const draftId=state.selected.id||null;state.selected=result.item;state.savedSnapshot=editorSnapshot(result.item);clearLocalDraft(previousKind,draftId);clearLocalDraft(result.item.kind,result.item.id||null);
    if(previousKind!==result.item.kind){state.page=result.item.kind;state.listTag="";state.listSort="updated";$$(".nav-item").forEach(item=>item.classList.toggle("is-active",item.dataset.page===state.page));$("#page-heading").textContent=labels[state.page]}
    await loadItems();drawItemList();drawEditor();$("#save-indicator").textContent="已保存 · "+new Date().toLocaleTimeString("zh-CN",{hour:"2-digit",minute:"2-digit"});
  }catch(error){indicator.textContent=error.message}
  finally{if($("#save-content"))$("#save-content").disabled=false}
}
async function deleteItem(){
  if(!state.selected.id||!window.confirm("确定把这条内容移入回收站吗？之后仍可恢复。"))return;
  const itemId=state.selected.id;clearLocalDraft(state.page,itemId);await api("/api/items/"+itemId,{method:"DELETE"});state.selected=null;state.savedSnapshot=null;await loadItems();drawItemList();drawEditor()
}
async function renderItemFiles(itemId){
  const list=$("#item-file-list");
  if(!list)return;
  try{
    const data=await api("/api/files?item_id="+encodeURIComponent(itemId));
    if(!state.selected||String(state.selected.id)!==String(itemId))return;
    list.innerHTML=data.files.length?data.files.map(file=>'<div class="item-file-row"><a href="/files/'+encodeURIComponent(file.id)+'" target="_blank">'+esc(file.name)+'</a><span>'+formatBytes(file.size)+'</span><button class="item-file-delete" data-id="'+esc(file.id)+'" title="移入回收站">×</button></div>').join(""):'<span class="attachment-hint">还没有关联文件</span>';
    $("#item-file-input").onchange=()=>uploadItemFile($("#item-file-input").files[0],itemId);
    $$(".item-file-delete").forEach(button=>button.onclick=async()=>{if(window.confirm("把这个附件移入回收站吗？之后仍可恢复。")){await api("/api/files/"+encodeURIComponent(button.dataset.id),{method:"DELETE"});await renderItemFiles(itemId)}});
  }catch(error){list.innerHTML='<span class="attachment-hint">附件列表暂时不可用</span>'}
}
async function uploadItemFile(file,itemId){
  if(!file)return;
  const form=new FormData();form.append("file",file);form.append("item_id",String(itemId));
  try{await api("/api/files",{method:"POST",body:form});await renderItemFiles(itemId)}catch(error){window.alert(error.message)}
}
function renderFileList(files){
  const list=$("#file-list"),count=$("#file-count");
  if(count)count.textContent=files.length+" 个文件";
  if(!files.length){list.innerHTML=state.fileSearch?'<div class="empty-state"><strong>没有匹配文件</strong><p>试试文件名或关联内容标题中的其他关键词。</p></div>':'<div class="empty-state"><strong>还没有文件</strong><p>上传第一份资料，让它和你的思路放在一起。</p></div>';return}
  list.innerHTML=files.map(file=>'<div class="file-row"><span class="file-symbol">↧</span><div><a href="/files/'+encodeURIComponent(file.id)+'" target="_blank">'+esc(file.name)+'</a><div class="file-size">'+formatBytes(file.size)+" · "+formatDate(file.created_at,true)+(file.item_title?" · "+esc(file.item_title):"")+'</div></div><span class="spacer"></span><button class="file-delete" data-id="'+file.id+'" title="删除">×</button></div>').join("");
  $$(".file-delete").forEach(button=>button.onclick=async()=>{if(window.confirm("把这个文件移入回收站吗？之后仍可恢复。")){await api("/api/files/"+button.dataset.id,{method:"DELETE"});await loadFileList()}});
}
async function loadFileList(){
  if(state.fileSearchController)state.fileSearchController.abort();
  const controller=new AbortController();state.fileSearchController=controller;
  const query=state.fileSearch.trim(),suffix=query?"?q="+encodeURIComponent(query):"";
  try{
    const data=await api("/api/files"+suffix,{signal:controller.signal});
    if(!controller.signal.aborted&&state.page==="files")renderFileList(data.files||[]);
  }catch(error){if(error.name!=="AbortError"&&$("#file-list"))$("#file-list").innerHTML='<div class="empty-state"><strong>文件列表暂时不可用</strong><p>请稍后重试。</p></div>'}
}
async function renderFiles(){
  state.fileSearch="";
  $("#page-content").innerHTML='<div class="page-title-row"><div><h1>文件空间</h1><p>把论文、数据和项目资料放在一个可回看的位置。</p></div></div><section class="surface file-surface"><label id="upload-zone" class="upload-zone"><strong>拖拽文件到这里，或点击选择文件</strong><span>文件会保存在当前服务器的私有数据目录</span><small>单个文件最大 64 MB</small><input id="file-input" class="file-input" type="file"></label><div class="file-toolbar"><label class="input-with-icon file-search"><span>⌕</span><input id="file-search" class="control-input" type="search" placeholder="搜索文件名或关联内容" autocomplete="off"></label><span id="file-count" class="file-count"></span></div><div id="file-list" class="file-list"></div></section>';
  const zone=$("#upload-zone"),input=$("#file-input");input.onchange=()=>uploadFile(input.files[0]);["dragenter","dragover"].forEach(event=>zone.addEventListener(event,e=>{e.preventDefault();zone.classList.add("dragover")}));["dragleave","drop"].forEach(event=>zone.addEventListener(event,e=>{e.preventDefault();zone.classList.remove("dragover")}));zone.addEventListener("drop",e=>uploadFile(e.dataTransfer.files[0]));
  $("#file-search").oninput=event=>{state.fileSearch=event.target.value;clearTimeout(state.fileSearchTimer);state.fileSearchTimer=setTimeout(loadFileList,160)};
  await loadFileList();
}
function formatBytes(bytes){if(bytes<1024)return bytes+" B";if(bytes<1024*1024)return (bytes/1024).toFixed(1)+" KB";return (bytes/1024/1024).toFixed(1)+" MB"}
async function uploadFile(file){
  if(!file)return;
  const form=new FormData();form.append("file",file);
  try{await api("/api/files",{method:"POST",body:form});await renderFiles()}catch(error){window.alert(error.message)}
}
$("#settings-button").onclick=()=>$("#settings-menu").classList.toggle("is-hidden");
$("#export-data").onclick=()=>{$("#settings-menu").classList.add("is-hidden");const link=document.createElement("a");link.href="/api/export";link.download="workmoire-export.json";document.body.appendChild(link);link.click();link.remove()};
$("#import-data").onclick=()=>{$("#settings-menu").classList.add("is-hidden");$("#import-input").click()};
$("#import-input").onchange=async()=>{const file=$("#import-input").files[0];if(!file)return;try{const payload=JSON.parse(await file.text());const count=Array.isArray(payload.items)?payload.items.length:0;if(!window.confirm("将追加导入 "+count+" 条内容，已有内容不会被覆盖。继续吗？")){$("#import-input").value="";return}const result=await api("/api/import",{method:"POST",body:JSON.stringify(payload)});window.alert("已导入 "+result.imported_items+" 条内容。文件附件元数据已跳过，请使用备份包恢复文件。");$("#import-input").value="";await goPage("dashboard")}catch(error){window.alert(error.message);$("#import-input").value=""}};
$("#logout").onclick=async()=>{await api("/api/logout",{method:"POST"});state.authenticated=false;state.focusMode=false;document.body.classList.remove("editor-focus-mode");showApp(false);setAuthMode(false)};
$("#change-password").onclick=()=>{$("#settings-menu").classList.add("is-hidden");$("#password-message").textContent="";$("#password-dialog").showModal()};
$("#password-form").addEventListener("submit",async event=>{if(event.submitter?.value==="cancel")return;event.preventDefault();$("#password-message").textContent="";try{await api("/api/password",{method:"POST",body:JSON.stringify({old_password:$("#old-password").value,new_password:$("#new-password").value})});$("#password-message").textContent="密码已更新";setTimeout(()=>$("#password-dialog").close(),500)}catch(error){$("#password-message").textContent=error.message}});
$("#assistant-close").onclick=()=>$("#assistant-dialog").close();$("#assistant-run").onclick=runAssistant;$("#assistant-apply-summary").onclick=()=>applyAssistantResult("summary");$("#assistant-apply-content").onclick=()=>applyAssistantResult("content");
$("#capture-form").addEventListener("submit",saveCapture);
$("#capture-title").addEventListener("input",scheduleCaptureDraft);$("#capture-content").addEventListener("input",scheduleCaptureDraft);$("#restore-capture-draft").onclick=restoreCaptureDraft;$("#discard-capture-draft").onclick=discardCaptureDraft;
$("#global-search-trigger").onclick=()=>{$("#search-dialog").showModal();$("#global-search").focus()};
async function searchGlobal(query){
  const box=$("#search-results");
  if(state.searchController)state.searchController.abort();
  if(!query){box.innerHTML='<div class="search-empty">输入关键词开始搜索</div>';return}
  const controller=new AbortController();state.searchController=controller;box.innerHTML='<div class="search-empty">搜索中…</div>';
  try{
    const kind=$("#global-search-kind").value,status=$("#global-search-status").value;
    const params=new URLSearchParams({q:query,limit:"30"});if(kind)params.set("kind",kind);if(status)params.set("status",status);
    const result=await api("/api/search?"+params.toString(),{signal:controller.signal});
    if(controller.signal.aborted)return;
    const items=result.items||[],files=result.files||[];
    const itemMarkup=items.map(item=>'<div class="search-result search-item-result" data-id="'+item.id+'" data-kind="'+item.kind+'">'+kindMark(item.kind)+'<div class="search-result-body"><strong>'+esc(item.title)+'</strong><div class="search-snippet">'+esc(item.snippet||item.summary||"暂无摘要")+'</div><div class="recent-meta">'+esc(labels[item.kind])+" · "+esc(statusLabels[item.status]||item.status)+" · "+relativeDate(item.updated_at)+'</div></div></div>').join("");
    const fileMarkup=files.map(file=>'<div class="search-result search-file-result" data-id="'+esc(file.id)+'"><span class="file-symbol">↧</span><div><strong>'+esc(file.name)+'</strong><div class="recent-meta">文件 · '+formatBytes(file.size)+(file.item_title?" · "+esc(file.item_title):"")+'</div></div></div>').join("");
    box.innerHTML=itemMarkup||fileMarkup?((itemMarkup?'<div class="search-section-label">内容</div>'+itemMarkup:"")+(fileMarkup?'<div class="search-section-label">文件</div>'+fileMarkup:"")):'<div class="search-empty">没有找到匹配内容或文件</div>';
    $$("#search-results .search-item-result").forEach(row=>row.onclick=async()=>{if(!await goPage(row.dataset.kind))return;$("#search-dialog").close();state.selected=state.items.find(item=>String(item.id)===row.dataset.id);state.savedSnapshot=editorSnapshot(state.selected);renderContentPage()});
    $$("#search-results .search-file-result").forEach(row=>row.onclick=()=>{window.open("/files/"+encodeURIComponent(row.dataset.id),"_blank","noopener")});
  }catch(error){if(error.name!=="AbortError")box.innerHTML='<div class="search-empty">搜索暂时不可用，请稍后重试</div>'}
}
$("#global-search").oninput=()=>searchGlobal($("#global-search").value.trim());
$("#global-search-kind").onchange=()=>searchGlobal($("#global-search").value.trim());
$("#global-search-status").onchange=()=>searchGlobal($("#global-search").value.trim());
document.addEventListener("keydown",event=>{if((event.ctrlKey||event.metaKey)&&event.shiftKey&&event.key.toLowerCase()==="n"){event.preventDefault();openCapture()}if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==="k"){event.preventDefault();$("#search-dialog").showModal();$("#global-search").focus()}if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==="s"&&state.selected){event.preventDefault();saveItem()}if((event.ctrlKey||event.metaKey)&&event.key==="Enter"&&state.selected){event.preventDefault();saveItem()}if(event.key==="Escape"){$("#settings-menu")?.classList.add("is-hidden")}});
$("#mobile-menu").onclick=()=>$(".sidebar").classList.toggle("is-open");
refreshServiceStatus();setInterval(refreshServiceStatus,60000);
boot();
