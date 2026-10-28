import {test} from 'node:test';
import assert from 'node:assert/strict';
import {slashCommands,searchSlashCommands} from '../web/slash-commands.mjs';
const first=query=>searchSlashCommands(query)[0]?.id;

test('code supports the requested shorthand, pinyin initials, Chinese and English',()=>{
 for(const query of ['ddm','dmk','dm','代码','代码块','daimakuai','dai ma kuai','code block','CODEBLOCK','ｄｄｍ'])assert.equal(first(query),'code',query);
});
test('quotation and checklist synonyms lead to the intended block',()=>{
 for(const query of ['yy','cite','引用','引用格式','yinyong','block quote','yy cite','引用 cite'])assert.equal(first(query),'quote',query);
 for(const query of ['todo','db','dbqd','待办','待办勾选框','复选框','task list','to do','待办 checkbox'])assert.equal(first(query),'task',query);
});
test('all block labels have usable initials or familiar abbreviations',()=>{
 for(const [query,id] of [['zw','paragraph'],['bt1','heading-1'],['bt 2','heading-2'],['bt3','heading-3'],['wxlb','list'],['yxlb','ordered-list'],['bg','table'],['gs','formula'],['hngs','inline-math'],['tp','image'],['PDF','pdf'],['wdlj','document-link'],['fgx','divider']])assert.equal(first(query),id,query);
});
test('multiple terms match across aliases without depending on word order',()=>{
 assert.equal(first('block code'),'code');assert.equal(first('inline math'),'inline-math');assert.equal(first('math inline'),'inline-math');assert.equal(first(' YY, CITE '),'quote');assert.equal(first('代码 python'),'code');
 assert.deepEqual(searchSlashCommands('code quote'),[]);assert.deepEqual(searchSlashCommands('unrecognizedxyz'),[]);
});
test('exact labels and aliases outrank matches in descriptions',()=>{
 assert.equal(first('引用'),'quote');assert.ok(searchSlashCommands('引用').some(command=>command.id==='document-link'));
 assert.equal(first('公式'),'formula');assert.equal(first('math'),'formula');assert.equal(first('link'),'document-link');
});
test('empty search preserves the catalogue and searches never mutate command data',()=>{
 const before=JSON.stringify(slashCommands);assert.deepEqual(searchSlashCommands('  '),slashCommands);searchSlashCommands('引用');searchSlashCommands('ddm');assert.equal(JSON.stringify(slashCommands),before);
});
