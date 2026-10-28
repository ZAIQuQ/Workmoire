const seconds=value=>{const n=Math.max(0,Math.ceil(value));return value<1?'不足 1 秒':n<60?n+' 秒':Math.floor(n/60)+' 分'+(n%60?' '+n%60+' 秒':'钟');};
const bytes=value=>value<1024*1024?(value/1024).toFixed(0)+' KB':(value/1024/1024).toFixed(1)+' MB';
const historyKey='workmoire:operation-durations:v1';
function samples(){try{const data=JSON.parse(localStorage.getItem(historyKey)||'{}');return data&&typeof data==='object'&&!Array.isArray(data)?data:{};}catch{return {};}}
function remember(kind,value){if(!Number.isFinite(value)||value<=0)return;try{const data=samples();data[kind]=[...(Array.isArray(data[kind])?data[kind]:[]),value].slice(-12);localStorage.setItem(historyKey,JSON.stringify(data));}catch{}}
function estimate(kind,fallback){const stored=samples()[kind],values=(Array.isArray(stored)?stored:[]).filter(n=>Number.isFinite(n)&&n>0).sort((a,b)=>a-b);return values.length?values[Math.floor(values.length/2)]:fallback;}
export function progressPanel(parent,label){
 const root=document.createElement('div');root.className='operation-progress';root.hidden=true;const title=document.createElement('div'),name=document.createElement('span'),percent=document.createElement('span');title.className='operation-progress-head';name.textContent=label;name.setAttribute('role','status');title.append(name,percent);const bar=document.createElement('progress');bar.max=100;bar.setAttribute('aria-label',label);const detail=document.createElement('div');detail.className='operation-progress-detail';root.append(title,bar,detail);parent.append(root);
 let began=0,timer=0,draw=null,stageStart=0,stageKey='',pageSamples=[],elapsedFloor=0;
 function show(){if(!began)began=performance.now();root.hidden=false;root.classList.remove('is-failed');if(!timer)timer=setInterval(()=>draw?.(),300);}
 function paint(value,title,text){name.textContent=title;if(value===null){bar.removeAttribute('value');percent.textContent='';}else{bar.value=Math.max(0,Math.min(100,value));percent.textContent=Math.floor(value)+'%';}detail.textContent=text;}
 return {
  root,
  stage(title,key='',fallback=2){show();stageStart=performance.now();stageKey=key;draw=()=>{const elapsed=(performance.now()-stageStart)/1000,expected=estimate(key,fallback);paint(null,title,'已用 '+seconds(elapsed)+(elapsed<expected?' · 预计还需 '+seconds(expected-elapsed):' · 正在处理'));};draw();},
  transfer(event){show();draw=()=>{const elapsed=(performance.now()-began)/1000,now=performance.now(),stalled=now-event.sampleAt>5000;const remaining=event.rate>0&&!stalled?(event.total-event.loaded)/event.rate:null;paint(event.total?event.loaded/event.total*100:null,label,bytes(event.loaded)+(event.total?' / '+bytes(event.total):'')+' · 已用 '+seconds(elapsed)+(remaining!==null&&event.loaded<event.total?' · 预计还需 '+seconds(remaining):stalled?' · 等待网络响应':''));};draw();},
  pages(done,total){show();if(stageKey!=='pdf-page'){stageStart=performance.now();stageKey='pdf-page';pageSamples=[];}pageSamples.push([performance.now(),done]);if(pageSamples.length>8)pageSamples.shift();
   draw=()=>{const now=performance.now(),elapsed=(now-stageStart)/1000,last=pageSamples.at(-1),first=pageSamples[Math.min(1,pageSamples.length-1)],rate=last[1]>first[1]?(last[0]-first[0])/1000/(last[1]-first[1]):null,stalled=rate!==null&&(now-last[0])/1000>Math.max(3,rate*3);const remaining=rate!==null&&!stalled?Math.max(0,total-done)*rate:null;paint(total?done/total*100:null,'提取 PDF 文字',done+' / '+total+' 页 · 已用 '+seconds(elapsed)+(done<total?(remaining===null?' · 正在估算剩余时间':' · 预计还需 '+seconds(remaining)):''));};draw();
  },
  analysis(status){show();const received=performance.now();elapsedFloor=Math.max(elapsedFloor,status.elapsed_seconds);draw=()=>{const running=status.elapsed_seconds+(performance.now()-received)/1000,elapsed=Math.max((performance.now()-began)/1000,running),e=status.estimate,over=running>e.high;const stage=status.stage==='preparing'?'准备论文材料':status.stage==='formatting'?'整理分析结果':'AI 分析论文';paint(over?null:Math.min(95,running/Math.max(1,e.seconds)*90),stage+' · 预估进度','已用 '+seconds(elapsed)+(over?' · 本次已超过常见耗时，仍在处理':' · 预计还需 '+seconds(Math.max(1,e.low-running))+'–'+seconds(Math.max(2,e.high-running)))+(e.samples?'（依据近期耗时）':'（首次估计）'));};draw();},
  done(text='已完成'){if(stageKey&&stageKey!=='pdf-page')remember(stageKey,(performance.now()-stageStart)/1000);clearInterval(timer);timer=0;paint(100,text,'用时 '+seconds(Math.max((performance.now()-began)/1000,elapsedFloor)));draw=null;},
  fail(text){clearInterval(timer);timer=0;root.hidden=false;root.classList.add('is-failed');paint(0,text,'操作未完成');percent.textContent='';draw=null;},
  reset(){clearInterval(timer);timer=0;draw=null;began=0;stageStart=0;stageKey='';pageSamples=[];elapsedFloor=0;root.hidden=true;},
  destroy(){clearInterval(timer);root.remove();}
 };
}
export function uploadFile(file,{itemId=null,onProgress=()=>{},onTransferComplete=()=>{}}={}){
 return new Promise((resolve,reject)=>{const xhr=new XMLHttpRequest(),points=[];xhr.open('POST','/api/files/upload');xhr.withCredentials=true;xhr.timeout=600000;xhr.responseType='json';xhr.setRequestHeader('Content-Type',file.type||'application/octet-stream');xhr.setRequestHeader('X-File-Name',encodeURIComponent(file.name));if(itemId)xhr.setRequestHeader('X-Item-Id',String(itemId));
 const started=performance.now();points.push([started,0]);
 xhr.upload.onprogress=event=>{const now=performance.now();points.push([now,event.loaded]);while(points.length>2&&now-points[0][0]>8000)points.shift();const first=points[0],elapsed=(now-first[0])/1000,rate=elapsed>.15?(event.loaded-first[1])/elapsed:0;onProgress({loaded:event.loaded,total:event.lengthComputable?event.total:file.size,rate,sampleAt:now});};
 xhr.upload.onload=()=>onTransferComplete();
 xhr.onload=()=>{if(xhr.status>=200&&xhr.status<300)resolve(xhr.response);else{const error=new Error(xhr.response?.error||'文件上传失败，请重试');error.status=xhr.status;reject(error);}};
 xhr.onerror=()=>reject(new Error('网络连接失败，请重试上传'));xhr.ontimeout=()=>reject(new Error('上传超时，请检查网络后重试'));xhr.onabort=()=>reject(new Error('上传已取消'));xhr.send(file);
 });
}
export async function trackPaperJob(initial,request,panel,isOpen=()=>true){
 let status=initial,failures=0;panel.analysis(status);
 while(status.status==='running'){
  await new Promise(resolve=>setTimeout(resolve,650));if(!isOpen())throw new Error('分析窗口已关闭');
  try{status=await request('/api/papers/jobs/'+status.job_id,{signal:AbortSignal.timeout(8000)});if(!isOpen())throw new Error('分析窗口已关闭');failures=0;panel.analysis(status);}catch(error){if(!isOpen())throw error;if(error.status===401||error.status===404)throw error;if(++failures>=3)throw new Error('暂时无法读取分析进度，请稍后重试');}
 }
 if(status.status!=='completed')throw new Error(status.error||'论文分析失败，请重试');panel.done('论文分析完成');return status.result;
}
