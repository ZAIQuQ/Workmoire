# 论文阅读台 · Paper reading desk

打开含有本地 PDF 的论文资料或文档，点击右上角 **阅读台**。左侧显示原文，右侧使用当前文档的富文本笔记。标题、保存、编辑/阅读切换和目录集中在紧凑顶栏；编辑工具栏可以按需展开。

## 边读边写

- 拖动中间分隔线调整原文与笔记宽度，也可聚焦分隔线后按方向键微调。拖动时按 Esc 取消本次调整。
- 同一文档有多份 PDF 时，在原文上方选择附件。来源只使用已上传附件；外部 PDF 链接继续提示手动上传。
- 手机使用 **原文 / 笔记** 切换。两侧保留各自的状态；插入引用后自动切到笔记。
- 点击 **退出阅读台**，或在没有展开菜单时按 Esc，返回原来的文档布局。
- 焦点在 PDF 内时，Ctrl/Cmd+S 保存当前笔记，Ctrl/Cmd+F 查找原文；Ctrl/Cmd+Shift+Enter 在原文与笔记之间切换。Esc 先取消框选或关闭搜索，再退出阅读台。
- 本机记住 PDF 页码、缩放、笔记阅读位置和栏宽。PDF 按附件及阅读场景保存状态，阅读台与普通内嵌阅读互不覆盖；重新识别到不同 PDF 指纹时忽略旧位置。这些偏好不会修改文档或进入分享快照。

## 引用与回到原文

1. 在左侧 PDF 中选中文字，点击底部 **引用到笔记**。
2. 引用插入当前笔记光标所在内容块之后，保留已选中的笔记正文，附上来源与页码。
3. 写下自己的解释，再正常保存文档。引用插入本身只修改草稿，也可以单独撤销。
4. 点击引用下方的页码，阅读台会回到对应 PDF 页面。编辑和阅读模式均可使用。

使用 **复制引用** 可复制包含来源链接的 Markdown，粘贴到已有 idea 或其他文档后继续编辑。一次引用最多 12,000 字。扫描 PDF 没有可选择文字时仍可阅读，文字引用需要 PDF 自身具有文本层。

新引用保存起始页的选区位置和 PDF 指纹，点击后定位到原文并短暂高亮；多页摘录标明页码范围，回跳到起始页。旧引用仍按页码打开。PDF 指纹不符时只打开引用页并提示核对，避免错误高亮。精确定位最多记录起始页的 32 个文字区域。

## 图表与公式框选

点击原文底部 **框选图表**，在同一页内拖动选择区域。确认 **插入笔记** 后才会生成并上传 PNG，取消不会留下附件。截图从 PDF 重新渲染，保留清晰度；单张限制为 400 万像素、最长边 3072px、12 MB。

图片与来源链接作为一次编辑插入笔记，可整体撤销。点击来源可回到对应区域；复制、导出和分享仍使用原来的附件机制。上传期间继续编辑时，插入点会跟随文档变化，保留新的文字和光标；中文输入尚未确认时等待输入完成。

[后台自动保存](autosave.md)默认同步确认插入后的内容。右上角提示同步异常时，建议暂时停止编辑并等待恢复；未确认的选区不会自动上传。

## 保存、导出与分享

引用使用标准文本块和受校验的附件页码链接，不引入新的文档类型。历史记录、草稿、Markdown 和完整归档保留引用；导入完整归档时重映射附件 ID，并保留页码。

分享只复制正文明确引用的附件，包括通过页码引用使用的 PDF。公共页面中的引用指向该分享自己的附件副本，打开时仍检查密码保护、有效期和撤销状态，不暴露私有附件地址。公共 PDF 阅读器不提供编辑笔记入口。

## English

Open **阅读台** in a document containing an uploaded PDF. Read the source beside
the existing rich-text notes, resize the divider, and use Original / Notes tabs
on phones. Local view preferences remember PDF pages and zoom independently from
the ordinary embedded viewer, as well as note position and split width.

Select PDF text and choose **引用到笔记** to insert a source quotation after the
current note block. It remains an unsaved edit until normal Save. Page citations
reopen the source at the cited page. **复制引用** copies Markdown for use in an
idea or another note. New citations retain bounded selection geometry and a PDF
fingerprint for precise, temporary highlighting; legacy citations keep page
navigation. A mismatched fingerprint displays a notice instead of highlighting.

Choose **框选图表**, drag within a page, then explicitly confirm insertion to
render and upload a bounded PNG with its source citation. Cancellation creates
no attachment. The image and citation undo together. PDF-focused save, search,
Escape and source/notes keyboard navigation work without recreating the viewer.

References survive history and exports; archives remap file IDs without losing
page numbers. Shares use scoped attachment copies and retain all existing access
controls. Local reading positions are not published.

## Related blocks and shared reading

Use `/latex` in a normal note to insert a source-editable LaTeX block. Write mode
accepts the local TeX/KaTeX syntax supported by the renderer; Preview shows the
rendered result. Markdown prose, tables, inline math and fenced code are detected and shown through
the safe Markdown fallback, which is useful for OpenReview-style response text.
The block keeps its source and character count through normal save, history and
export. Shared readers receive the rendered block, can open the read-only Write
tab and copy the source, and see the right-hand outline without editing.
