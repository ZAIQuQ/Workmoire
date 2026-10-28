// Stable bookmark colors: display preferences are never written into documents.
export const PAPER_TAG='论文';
export const BLOG_TAG='博客';
export const builtinTag=kind=>({paper:PAPER_TAG,blog:BLOG_TAG})[kind]||'';
export const isBuiltin=tag=>tag===PAPER_TAG||tag===BLOG_TAG;
export const tagName=value=>String(value).normalize('NFKC').trim().replace(/^#+/,'').trim().replace(/\s+/g,' ');
export const tagKey=value=>tagName(value).toLowerCase();
export function tagColor(value){
 if(tagKey(value)===PAPER_TAG)return 'blue';
 if(tagKey(value)===BLOG_TAG)return 'copper';
 let hash=2166136261;for(const char of tagKey(value)){hash^=char.codePointAt(0);hash=Math.imul(hash,16777619);}
 return ['blue','teal','amber','violet','rose','slate','cyan','copper'][(hash>>>0)%8];
}
export function documentTags(value,kind){
 const tags=String(value||'').split(',').filter(Boolean);
 const builtin=builtinTag(kind);return builtin?[builtin,...tags.filter(tag=>tag!==builtin)]:tags;
}
