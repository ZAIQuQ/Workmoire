const {test,expect}=require('@playwright/test');
const fs=require('node:fs');
const path=require('node:path');
const pixel=Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aX1cAAAAASUVORK5CYII=','base64');
async function login(page){await page.goto('/');await page.locator('#auth-username').fill('demo-reader');await page.locator('#auth-password').fill('synthetic-password');await page.locator('#auth-submit').click();await expect(page.locator('#app-view')).toBeVisible();await expect(page.locator('#item-list')).toBeVisible();}
async function blank(page,title){await page.locator('#new-document').click();await page.locator('[data-template="blank"]').click();await page.locator('#edit-title').fill(title);await expect(page.locator('.cm-content')).toBeVisible();}
async function setContent(page,text){await page.evaluate(text=>state.editor.setValue(text),text);}
async function content(page){return page.evaluate(()=>state.editor.getValue());}
async function save(page){await page.locator('#save-content').click();await expect(page.locator('#save-state')).toHaveText('已保存');}
test('login, reduced navigation, local libraries and rich Markdown',async({page})=>{
 const errors=[];page.on('pageerror',error=>errors.push(error.message));await login(page);
 await expect(page.locator('.main-nav .nav-item')).toHaveCount(3);
 await page.locator('[data-open="1"]').click();await expect(page.locator('.katex').first()).toBeVisible();
 await expect(page.locator('.prose table')).toHaveCount(1);await expect(page.locator('.prose .hljs-keyword').first()).toBeVisible();
 await page.locator('#content-preview .task-check').first().check();await expect.poll(()=>content(page)).toContain('- [x] 比较局部窗口');
 await save(page);await page.screenshot({path:'artifacts/editor-desktop.png',fullPage:true});expect(errors).toEqual([]);
});
test('toolbar, formulas, tables, symbols, safe preview and draft restore',async({page})=>{
 await login(page);await blank(page,'浏览器测试：编辑与草稿');
 await page.locator('[data-command="bold"]').click();await expect.poll(()=>content(page)).toContain('**加粗文本**');
 await setContent(page,'# 测试标题\n\nInline $x^2$\n\n$$\n\\sum_{i=1}^{n} i\n$$\n\n| A | B |\n| --- | --- |\n| 1 | 2 |\n\n<img src=x onerror="window.injected=1">\n\n[unsafe](javascript:alert(1))\n');
 await expect(page.locator('#content-preview .katex')).toHaveCount(2);await expect(page.locator('#content-preview table')).toHaveCount(1);
 expect(await page.evaluate(()=>window.injected)).toBeUndefined();await expect(page.locator('#content-preview a[href^="javascript"]')).toHaveCount(0);
 await save(page);const id=await page.evaluate(()=>state.current.id);await setContent(page,'草稿中的新思路');await page.waitForTimeout(400);
 page.once('dialog',dialog=>dialog.accept());await page.locator('[data-page="papers"]').click();await page.locator('[data-page="documents"]').click();await page.locator('[data-open="'+id+'"]').click();await expect(page.locator('#restore-draft')).toBeVisible();await page.locator('#restore-draft').click();await expect.poll(()=>content(page)).toBe('草稿中的新思路');
});
test('image uploads, paste once, PDF embeds and authenticated file responses',async({page,request})=>{
 await login(page);await blank(page,'浏览器测试：图片与 PDF');
 await page.locator('#asset-input').setInputFiles({name:'fixture.png',mimeType:'image/png',buffer:pixel});
 await expect(page.locator('#content-preview img')).toHaveCount(1);await expect.poll(()=>page.locator('#content-preview img').evaluate(el=>el.naturalWidth)).toBeGreaterThan(0);
 await page.evaluate(()=>{const data=new DataTransfer();data.items.add(new File([new Uint8Array([137,80,78,71,13,10,26,10])],'pasted.png',{type:'image/png'}));document.querySelector('#editor').dispatchEvent(new ClipboardEvent('paste',{clipboardData:data,bubbles:true,cancelable:true}));});
 await expect.poll(()=>content(page)).toContain('pasted.png');
 const fixture=await page.request.get('/files/'+('b'.repeat(32))+'?inline=1');expect(fixture.status()).toBe(200);const pdf=await fixture.body();
 await page.locator('#asset-input').setInputFiles({name:'fixture.pdf',mimeType:'application/pdf',buffer:pdf});await expect(page.locator('#content-preview iframe')).toHaveCount(1);
 const reader=page.frameLocator('#content-preview iframe');await expect(reader.locator('.page canvas').first()).toBeVisible();await expect(reader.locator('.textLayer')).toContainText('Workmoire');await reader.locator('#pdf-zoom').selectOption('1.5');await setContent(page,(await content(page))+'\n继续记录阅读时的想法。');await page.waitForTimeout(300);await expect(reader.locator('#pdf-zoom')).toHaveValue('1.5');
 await save(page);const id=await page.evaluate(()=>state.current.id);const data=await (await page.request.get('/api/files?item_id='+id)).json();expect(data.files).toHaveLength(3);
 const pdfFile=data.files.find(f=>f.name==='fixture.pdf');const response=await page.request.get('/files/'+pdfFile.id+'?inline=1',{headers:{Range:'bytes=0-4'}});expect(response.status()).toBe(206);expect((await response.body()).toString()).toBe('%PDF-');
 const anonymous=await request.get('/files/'+pdfFile.id+'?inline=1');expect(anonymous.status()).toBe(401);
});
test('paper lookup to Codex draft requires explicit insertion and save',async({page})=>{
 await login(page);await page.locator('[data-page="papers"]').click();await page.locator('#paper-quick-start').click();await page.locator('#paper-reference').fill('Synthetic paper title');await page.locator('#paper-lookup').click();await expect(page.locator('.paper-candidate')).toHaveCount(1);
 const before=await (await page.request.get('/api/items?kind=paper')).json();await page.locator('[data-paper-generate="0"]').click();await expect(page.locator('#paper-result')).toBeVisible();
 const generated=await (await page.request.get('/api/items?kind=paper')).json();expect(generated.total).toBe(before.total);
 await page.locator('#paper-use').click();await expect(page.locator('#edit-title')).toHaveValue('Synthetic paper for browser verification');expect(await page.evaluate(()=>state.current.id)).toBeNull();
 const notSaved=await (await page.request.get('/api/items?kind=paper')).json();expect(notSaved.total).toBe(before.total);await save(page);const saved=await (await page.request.get('/api/items?kind=paper')).json();expect(saved.total).toBe(before.total+1);
});
test('link documents, simple relation view and reversible trash',async({page})=>{
 await login(page);await blank(page,'浏览器测试：关联文档');await page.locator('#document-link-button').click();await page.locator('#link-search').fill('稀疏注意力');await page.locator('[data-link-id="1"]').click();await save(page);const id=await page.evaluate(()=>state.current.id);const links=await (await page.request.get('/api/items/'+id+'/links')).json();expect(links.items.some(x=>x.id===1)).toBeTruthy();
 await page.locator('[data-page="relations"]').click();await page.locator('[data-focus-id="'+id+'"]').click();await expect(page.locator('.map-related-card')).toHaveCount(1);await page.screenshot({path:'artifacts/relations-desktop.png',fullPage:true});await page.locator('#map-current').click();await page.locator('#inspector-toggle').click();page.once('dialog',dialog=>dialog.accept());await page.locator('#delete-document').click();await expect(page.locator('#editor .editor-welcome')).toBeVisible();await page.locator('#settings-button').click();await page.locator('[data-settings-page="trash"]').click();await page.locator('[data-trash-restore="items:'+id+'"]').click();await expect.poll(async()=>{const r=await page.request.get('/api/items/'+id);return r.status();}).toBe(200);
});
test('conflicting saves preserve local writing',async({page})=>{
 await login(page);await blank(page,'浏览器测试：冲突保护');await setContent(page,'最初正文');await save(page);const original=await page.evaluate(()=>({...state.current}));await setContent(page,'本机未保存的正文');const update=await page.request.put('/api/items/'+original.id,{data:{kind:'note',title:original.title,content:'另一个窗口的更新',base_updated_at:original.updated_at}});expect(update.status()).toBe(200);
 await page.locator('#save-content').click();await expect(page.locator('#conflict-notice')).toBeVisible();expect(await content(page)).toBe('本机未保存的正文');await page.locator('#load-current-version').click();await expect.poll(()=>content(page)).toBe('另一个窗口的更新');await expect(page.locator('#copy-stale-draft')).toBeVisible();await expect(page.locator('#restore-draft')).toHaveCount(0);
});
test('mobile editing and paper PDF reading fit the viewport',async({page})=>{
 await page.setViewportSize({width:390,height:844});await login(page);await page.locator('[data-open="2"]').click();await expect(page.locator('#back-to-list')).toBeVisible();await page.locator('button[data-mode="read"]').click();await expect(page.locator('.pdf-embed iframe')).toBeVisible();await expect(page.frameLocator('.pdf-embed iframe').locator('.page canvas').first()).toBeVisible();expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);await page.screenshot({path:'artifacts/editor-mobile.png',fullPage:true});
 for(const width of [320,390]){await page.setViewportSize({width,height:844});const controls=await page.frameLocator('.pdf-embed iframe').locator('.pdf-toolbar').evaluate(el=>{const bar=el.getBoundingClientRect();return Array.from(el.children).filter(child=>getComputedStyle(child).display!=='none').every(child=>{const r=child.getBoundingClientRect();return r.left>=bar.left&&r.right<=bar.right;});});expect(controls).toBeTruthy();expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);}
 await page.locator('#back-to-list').click();await expect(page.locator('#item-list')).toBeVisible();await page.locator('#mobile-menu').click();await expect(page.locator('.sidebar')).toHaveClass(/is-open/);
});
test('typing during a save is preserved and remains unsaved',async({page})=>{
 await login(page);await blank(page,'浏览器测试：保存期间继续输入');await setContent(page,'第一版');await save(page);const id=await page.evaluate(()=>state.current.id);
 await setContent(page,'发出的第二版');let release;const blocked=new Promise(resolve=>release=resolve);await page.route('**/api/items/'+id,async route=>{if(route.request().method()==='PUT'){await blocked;await route.continue();}else await route.continue();});
 await page.locator('#save-content').click();await expect(page.locator('#save-state')).toHaveText('保存中…');await setContent(page,'请求发出后又写下的一行');release();await expect(page.locator('#save-content')).toBeEnabled();await expect.poll(()=>content(page)).toBe('请求发出后又写下的一行');await expect(page.locator('#save-state')).toHaveText('未保存 · 本机草稿');
 const saved=await (await page.request.get('/api/items/'+id)).json();expect(saved.item.content).toBe('发出的第二版');await page.unroute('**/api/items/'+id);await save(page);const final=await (await page.request.get('/api/items/'+id)).json();expect(final.item.content).toBe('请求发出后又写下的一行');
});
test('an upload completing after the first save stays associated on the next save',async({page})=>{
 await login(page);await blank(page,'浏览器测试：上传与保存交错');let release,received;const waiting=new Promise(resolve=>release=resolve),started=new Promise(resolve=>received=resolve);
 await page.route('**/api/files',async route=>{if(route.request().method()!=='POST'){await route.continue();return;}const response=await route.fetch();received();await waiting;await route.fulfill({response});});
 await page.locator('#asset-input').setInputFiles({name:'late-image.png',mimeType:'image/png',buffer:pixel});await started;await save(page);const id=await page.evaluate(()=>state.current.id);release();await expect(page.locator('#content-preview img')).toHaveCount(1);await expect(page.locator('#save-state')).toHaveText('未保存 · 本机草稿');await save(page);const files=await (await page.request.get('/api/files?item_id='+id)).json();expect(files.files).toHaveLength(1);expect(files.files[0].name).toBe('late-image.png');
});

test('local visual resources render sharply and keep their intrinsic proportions',async({page})=>{
 const remote=[];const failed=[];page.on('request',request=>{if(/^https?:/.test(request.url())&&!request.url().startsWith('http://127.0.0.1:8765/'))remote.push(request.url());});page.on('response',response=>{if(response.url().includes('/static/')&&response.status()>=400)failed.push(response.url());});
 await page.goto('/');await expect(page.locator('.auth-illustration')).toBeVisible();await page.evaluate(()=>document.fonts.ready);
 const art=await page.locator('.auth-illustration').evaluate(el=>({loaded:el.complete&&el.naturalWidth>0,actual:el.getBoundingClientRect().width/el.getBoundingClientRect().height,intrinsic:el.naturalWidth/el.naturalHeight}));expect(art.loaded).toBeTruthy();expect(art.actual).toBeCloseTo(art.intrinsic,2);
 await page.locator('#auth-username').fill('demo-reader');await page.locator('#auth-password').fill('synthetic-password');await page.locator('#auth-submit').click();await expect(page.locator('.welcome-illustration')).toBeVisible();await page.evaluate(()=>document.fonts.ready);
 const fonts=await page.evaluate(()=>Array.from(document.fonts).filter(font=>font.status==='loaded').map(font=>font.family));expect(fonts.some(font=>font.includes('Geist'))).toBeTruthy();expect(fonts.some(font=>font.includes('Noto Sans SC'))).toBeTruthy();await expect(page.locator('.main-nav svg.icon')).toHaveCount(3);
 await blank(page,'浏览器测试：图片比例');const image=await page.evaluate(()=>{const canvas=document.createElement('canvas');canvas.width=960;canvas.height=540;const ctx=canvas.getContext('2d');ctx.fillStyle='#e8eee6';ctx.fillRect(0,0,960,540);ctx.fillStyle='#365648';ctx.fillRect(80,80,800,30);return canvas.toDataURL('image/png').split(',')[1];});await page.locator('#asset-input').setInputFiles({name:'synthetic-wide-diagram.png',mimeType:'image/png',buffer:Buffer.from(image,'base64')});
 const preview=page.locator('#content-preview img');await expect(preview).toBeVisible();await expect.poll(()=>preview.evaluate(el=>el.naturalWidth)).toBe(960);
 for(const viewport of [{width:1440,height:1000},{width:1280,height:800},{width:1024,height:768},{width:768,height:1024},{width:390,height:844},{width:320,height:740}]){
   await page.setViewportSize(viewport);await page.locator('button[data-mode="read"]').click();const bounds=await preview.evaluate(el=>{const rect=el.getBoundingClientRect();const pane=el.closest('.preview-pane').getBoundingClientRect();return{ratio:rect.width/rect.height,width:rect.width,pane:pane.width};});expect(bounds.ratio).toBeCloseTo(16/9,2);expect(bounds.width).toBeLessThanOrEqual(bounds.pane);expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(viewport.width);
 }
 expect(remote).toEqual([]);expect(failed).toEqual([]);
});

test('editor controls, independent reading scroll, mobile drawer and dialogs remain usable',async({page})=>{
 await page.emulateMedia({reducedMotion:'reduce'});await login(page);await page.locator('[data-open="1"]').click();await page.locator('button[data-mode="split"]').click();
 await expect(page.locator('.editor-toolbar > button[data-command="bold"] svg')).toHaveCount(1);await expect(page.locator('button[data-mode="split"]')).toHaveAttribute('aria-pressed','true');
 await page.locator('#content-preview').evaluate(el=>{el.scrollTop=el.scrollHeight;});expect(await page.locator('#content-preview').evaluate(el=>el.scrollTop)).toBeGreaterThan(0);expect(await page.evaluate(()=>window.scrollY)).toBe(0);await expect(page.locator('#save-content')).toBeInViewport();
 await page.locator('#focus-mode').click();await expect(page.locator('#focus-mode')).toHaveAttribute('aria-pressed','true');await page.keyboard.press('Escape');await expect(page.locator('#focus-mode')).toHaveAttribute('aria-pressed','false');
 for(const width of [390,320]){
   await page.setViewportSize({width,height:740});await expect.poll(()=>page.locator("#edit-title").evaluate(el=>el.scrollHeight-el.clientHeight)).toBeLessThanOrEqual(1);await page.locator('button[data-mode="write"]').click();await expect(page.locator('#save-content')).toBeInViewport();await expect(page.locator('.editor-toolbar .insert-menu summary')).toBeInViewport();await page.locator('.insert-menu summary').click();await expect(page.locator('.insert-options [data-command="pdf"]')).toBeInViewport();const popup=await page.locator(".insert-options").boundingBox();expect(popup.y).toBeGreaterThanOrEqual(0);expect(popup.y+popup.height).toBeLessThanOrEqual(740);await page.locator('.insert-options [data-command="table"]').click();await expect.poll(()=>content(page)).toContain('| 项目 | 说明 |');
   await page.locator('#mobile-menu').click();await expect(page.locator('#mobile-menu')).toHaveAttribute('aria-expanded','true');await expect(page.locator('#sidebar-backdrop')).toBeVisible();await page.locator('#sidebar-backdrop').click({position:{x:width-12,y:300}});await expect(page.locator('#mobile-menu')).toHaveAttribute('aria-expanded','false');await expect(page.locator('#sidebar-backdrop')).toBeHidden();
   await page.keyboard.press('Control+Shift+N');await expect(page.locator('#template-dialog')).toBeVisible();await expect(page.locator('.template-card svg')).toHaveCount(6);expect(await page.locator('#template-dialog').evaluate(el=>el.scrollWidth<=el.clientWidth)).toBeTruthy();await page.keyboard.press('Escape');
 }
 // Keep this fixture's edits browser-local; no production data is involved.
});
