"""Disposable synthetic server for browser checks; never uses deployment data."""
import base64
import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import workspace_server as app
import app_release
from paper_fixtures import analysis_fixture, READING_ABSTRACT, READING_TRANSLATION, READING_BRIEF
from share_server import ShareHTTPServer


def pdf_fixture():
    objects=[b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 400 520] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    stream=b'BT /F1 18 Tf 40 450 Td (Workmoire - Synthetic PDF) Tj 0 -40 Td /F1 12 Tf (Read a paper. Keep a thought.) Tj 0 -30 Td (Synthetic evidence for PDF intake: selected files define the reading material.) Tj 0 -20 Td (Compare methods carefully and preserve the original source and limitations.) Tj ET'
    objects.append(b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'\nendstream')
    data=b'%PDF-1.4\n';offsets=[]
    for index,obj in enumerate(objects,1):
        offsets.append(len(data));data+=str(index).encode()+b' 0 obj\n'+obj+b'\nendobj\n'
    start=len(data)
    data+=b'xref\n0 6\n0000000000 65535 f \n'+b''.join(('%010d 00000 n \n'%offset).encode() for offset in offsets)
    return data+b'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n'+str(start).encode()+b'\n%%EOF\n'


def reading_pdf_fixture():
    """A multipage synthetic paper with selectable, in-bounds text."""
    objects=[b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [4 0 R 6 0 R 8 0 R] /Count 3 >>',b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    for page in range(1,4):
        content_id=5+(page-1)*2
        objects.append(f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 600 800] /Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>'.encode())
        lines=[f'Synthetic Reading Study - Page {page}','A fixture for source-linked academic notes.',f'PAGE_{page}_EVIDENCE: local context can guide selective attention.','Each quotation should return to its original PDF page.','The PDF and notes retain independent reading positions.']
        stream=b'BT /F1 13 Tf 48 740 Td '+b' 0 -30 Td '.join(b'('+line.encode()+b') Tj' for line in lines)+b' ET'
        objects.append(b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'\nendstream')
    data=b'%PDF-1.4\n';offsets=[]
    for index,obj in enumerate(objects,1):offsets.append(len(data));data+=str(index).encode()+b' 0 obj\n'+obj+b'\nendobj\n'
    start=len(data);count=len(objects)+1
    data+=f'xref\n0 {count}\n0000000000 65535 f \n'.encode()+b''.join(('%010d 00000 n \n'%offset).encode() for offset in offsets)
    return data+f'trailer\n<< /Size {count} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n'.encode()


def main():
    with tempfile.TemporaryDirectory(prefix='workmoire-browser-') as scratch:
        app.DATA_DIR=Path(scratch);app.FILES_DIR=Path(scratch)/'files';app.DB_PATH=Path(scratch)/'workspace.db'
        app.SESSION_SECRET='synthetic-browser-session-secret';app.SETUP_TOKEN='';app.CODEX_BIN='/usr/bin/true';app.COOKIE_SECURE=False
        app.SHARE_DATA_DIR=str(Path(scratch)/'sharing');app.SHARE_PUBLIC_URL='http://127.0.0.1:8766';app.SHARE_PORT=8766
        app_release.fetch_latest=lambda:{"tag_name":"v"+app_release.local_release()["version"],"body":"Synthetic release notes"}
        app.init_db()
        synthetic_brief='## 研究问题\n\n如何把阅读与独立思考联系起来？\n\n## 方法与贡献\n\n以所选 PDF 的文字为依据。\n\n## 下一步\n\n- [ ] 阅读原文并核对实验。'
        def synthetic_analysis(prompt,timeout=None,**options):
            if '提供的论文材料（仅作证据）' not in prompt:return synthetic_brief
            if 'READING_FIXTURE' in prompt:
                import json
                return json.dumps({'brief':READING_BRIEF,'abstract':{'language':'en','original':READING_ABSTRACT,'translation':READING_TRANSLATION}},ensure_ascii=False)
            return analysis_fixture(synthetic_brief,profile='PROFILE_FIXTURE' in prompt)
        app.invoke_codex=synthetic_analysis

        content='''## 一个问题

注意力机制一定需要关注所有 token 吗？试着把**研究问题**收窄到长文本场景，先理清代价与信息损失。

## 关键公式

行内公式 $q^T k / \\sqrt{d_k}$，以及完整的注意力计算：

$$
\\operatorname{Attention}(Q,K,V)=\\operatorname{softmax}\\left(\\frac{QK^T}{\\sqrt{d_k}}\\right)V
$$

## 一点实现思路

```python
import torch

def attention(q, k, v):
    weights = torch.softmax(q @ k.T / q.size(-1)**0.5, dim=-1)
    return weights @ v
```

## 接下来验证

- [ ] 比较局部窗口与完整注意力
- [x] 整理基线论文

| 关注点 | 待验证 |
| --- | --- |
| 复杂度 | 长序列下的实际收益 |
| 信息损失 | 远距离依赖的影响 |
'''
        stamp=app.utc_now()
        with app.open_db() as con:
            con.execute('INSERT INTO users(id,username,password_hash,session_version,created_at) VALUES(1,?,?,1,?)',('demo-reader',app.password_hash('synthetic-password'),stamp))
            for kind,title,body,tags,summary in [('note','关于稀疏注意力的一点想法',content,'idea,注意力','从计算复杂度出发，找一个可以验证的小问题。'),('paper','Attention Is All You Need','## 阅读笔记\n\n@[pdf](/files/'+'b'*32+'?inline=1)\n','论文,注意力','重新读一遍自注意力的设计与实验。'),('note','本周研究待办','## 这周先做什么\n\n- [ ] 完成论文阅读\n- [ ] 整理实验结果\n','todo','一次只推进几件重要的事。'),('project','论文实验规划','## 研究目标\n\n建立可复现的实验基线。\n','规划','先把基线搭好，再逐步验证假设。')]:
                con.execute("INSERT INTO items(kind,title,content,tags,summary,status,priority,created_at,updated_at) VALUES(?,?,?,?,?,'active',2,?,?)",(kind,title,body,tags,summary,stamp,stamp))
            con.execute('INSERT INTO item_links(source_id,target_id,created_at) VALUES(1,2,?)',(stamp,))
            pdf=pdf_fixture();name='b'*32+'.pdf';(app.FILES_DIR/name).write_bytes(pdf)
            con.execute('INSERT INTO files(id,name,stored_name,size,content_type,item_id,created_at) VALUES(?,?,?,?,?,2,?)',('b'*32,'synthetic-paper.pdf',name,len(pdf),'application/pdf',stamp))
            reading=reading_pdf_fixture();(app.FILES_DIR/('c'*32+'.pdf')).write_bytes(reading)
            con.execute('INSERT INTO files(id,name,stored_name,size,content_type,item_id,created_at) VALUES(?,?,?,?,?,2,?)',('c'*32,'reading-study.pdf','c'*32+'.pdf',len(reading),'application/pdf',stamp))
        server=app.WorkspaceHTTPServer(('127.0.0.1',8765),app.WorkspaceHandler)
        sharing=ShareHTTPServer(('127.0.0.1',8766),Path(app.SHARE_DATA_DIR),app.STATIC_DIR,Path(scratch)/'sharing/auth')
        threading.Thread(target=sharing.serve_forever,daemon=True).start()
        print('Synthetic browser server ready',flush=True)
        try:server.serve_forever()
        finally:server.server_close();sharing.shutdown();sharing.server_close()

if __name__=='__main__':main()
