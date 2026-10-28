// A small, explicit vocabulary keeps command search predictable and local.
export const slashCommands = [
  {id:'paragraph',label:'正文',description:'普通段落',icon:'write',shortcut:'zw',aliases:['zw','dl','p','text','paragraph','正文','段落','zhengwen','duanluo']},
  {id:'heading-1',label:'标题 1',description:'一级标题',icon:'document',shortcut:'bt1',aliases:['bt1','h1','yjbt','title','title 1','heading 1','标题一','一级标题','biaoti1','yijibiaoti']},
  {id:'heading-2',label:'标题 2',description:'二级标题',icon:'document',shortcut:'bt2',aliases:['bt2','h2','ejbt','title 2','heading 2','标题二','二级标题','biaoti2','erjibiaoti']},
  {id:'heading-3',label:'标题 3',description:'三级标题',icon:'document',shortcut:'bt3',aliases:['bt3','h3','sjbt','title 3','heading 3','标题三','三级标题','biaoti3','sanjibiaoti']},
  {id:'list',label:'无序列表',description:'列出要点',icon:'list',shortcut:'wxlb',aliases:['wxlb','wx','ul','bullet','bullet list','unordered','unordered list','list','无序','列表','wuxuliebiao']},
  {id:'ordered-list',label:'有序列表',description:'按顺序编号',icon:'ordered',shortcut:'yxlb',aliases:['yxlb','yx','ol','ordered','ordered list','number','numbered list','有序','编号','youxuliebiao']},
  {id:'task',label:'待办清单',description:'勾选完成状态',icon:'task',shortcut:'db',aliases:['db','dbqd','gxk','fxk','todo','to do','task','task list','checkbox','checklist','check list','待办','待办事项','待办勾选框','勾选框','复选框','任务清单','daiban','daibanqingdan']},
  {id:'quote',label:'引用',description:'引用段落',icon:'quote',shortcut:'yy',aliases:['yy','cite','quote','blockquote','block quote','citation','引用格式','引文','yinyong']},
  // ddm is the user's preferred shortcut; dmk is also accepted as the initials of 代码块.
  {id:'code',label:'代码块',description:'语法高亮与语言切换',icon:'code',shortcut:'ddm',aliases:['ddm','dmk','dm','code','codeblock','code block','代码','daima','daimakuai','python','javascript']},
  {id:'table',label:'表格',description:'可直接编辑、调整列宽',icon:'table',shortcut:'bg',aliases:['bg','table','grid','biaoge']},
  {id:'formula',label:'公式',description:'LaTeX 块级公式',icon:'formula',shortcut:'gs',aliases:['gs','kjgs','gsk','math','latex','tex','formula','equation','block math','数学公式','块级公式','gongshi','kuaijigongshi']},
  {id:'inline-math',label:'行内公式',description:'在段落中插入公式',icon:'variable',shortcut:'hngs',aliases:['hngs','inline math','inline formula','inline equation','行内','hangneigongshi']},
  {id:'image',label:'图片',description:'上传、粘贴或使用链接',icon:'image',shortcut:'tp',aliases:['tp','image','img','photo','picture','插图','tupian']},
  {id:'pdf',label:'PDF',description:'在文档内阅读原文',icon:'book',shortcut:'pdf',aliases:['pdf','lw','yw','paper','论文','原文','pdf阅读器','lunwen','yuanwen']},
  {id:'document-link',label:'文档链接',description:'引用其他文档',icon:'relations',shortcut:'wdlj',aliases:['wdlj','lj','link','doc','document link','reference','ref','关联','wendanglianjie']},
  {id:'divider',label:'分隔线',description:'分隔文档内容',icon:'minus',shortcut:'fgx',aliases:['fgx','hr','divider','separator','horizontal rule','分割线','fengexian']},
];

function normalize(value){return String(value??'').normalize('NFKC').toLowerCase().trim().replace(/\s+/gu,' ');}
const compact=value=>value.replace(/\s+/gu,'');
const index=slashCommands.map((command,order)=>({
  command,order,label:normalize(command.label),description:normalize(command.description),
  aliases:[command.id.replaceAll('-',' '),...command.aliases].map(normalize),
})).map(entry=>({...entry,fields:[entry.label,...entry.aliases].flatMap(value=>[value,compact(value)])}));

export function searchSlashCommands(value){
  const query=normalize(value),terms=query.split(/[\s,]+/u).filter(Boolean),joined=compact(query);
  if(!terms.length)return [...slashCommands];
  const ranked=[];
  for(const entry of index){
    let score=0;
    for(const term of terms){
      let match=0;
      if(entry.fields.some(field=>field===term))match=100;
      else if(entry.fields.some(field=>field.startsWith(term)||field.split(' ').some(word=>word.startsWith(term))))match=70;
      else if(entry.fields.some(field=>field.includes(term)))match=40;
      else if(entry.description.includes(term))match=10;
      if(!match){score=-1;break;}
      score+=match;
    }
    if(score<0)continue;
    if(entry.label===query||compact(entry.label)===joined)score+=10000;
    else if(entry.aliases.some(alias=>alias===query||compact(alias)===joined))score+=9000;
    ranked.push({command:entry.command,score,order:entry.order});
  }
  return ranked.sort((a,b)=>b.score-a.score||a.order-b.order).map(entry=>entry.command);
}
