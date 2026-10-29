# 论文阅读台 · Paper reading desk

打开含有本地 PDF 的论文资料或文档，点击右上角 **阅读台**。左侧显示原文，右侧使用当前文档的富文本笔记。标题、保存、编辑/阅读切换和目录集中在紧凑顶栏；编辑工具栏可以按需展开。

## 边读边写

- 拖动中间分隔线调整原文与笔记宽度，也可聚焦分隔线后按方向键微调。拖动时按 Esc 取消本次调整。
- 同一文档有多份 PDF 时，在原文上方选择附件。来源只使用已上传附件；外部 PDF 链接继续提示手动上传。
- 手机使用 **原文 / 笔记** 切换。两侧保留各自的状态；插入引用后自动切到笔记。
- 点击 **退出阅读台**，或在没有展开菜单时按 Esc，返回原来的文档布局。
- 本机记住 PDF 页码、缩放、笔记阅读位置和栏宽。PDF 按附件及阅读场景保存状态，阅读台与普通内嵌阅读互不覆盖；重新识别到不同 PDF 指纹时忽略旧位置。这些偏好不会修改文档或进入分享快照。

## 引用与回到原文

1. 在左侧 PDF 中选中文字，点击底部 **引用到笔记**。
2. 引用插入当前笔记光标所在内容块之后，保留已选中的笔记正文，附上来源与页码。
3. 写下自己的解释，再正常保存文档。引用插入本身只修改草稿，也可以单独撤销。
4. 点击引用下方的页码，阅读台会回到对应 PDF 页面。编辑和阅读模式均可使用。

使用 **复制引用** 可复制包含来源链接的 Markdown，粘贴到已有 idea 或其他文档后继续编辑。一次引用最多 12,000 字。扫描 PDF 没有可选择文字时仍可阅读，文字引用需要 PDF 自身具有文本层。

首版支持页码回跳。精确文字高亮定位、框选图片与批量标注整理留待后续迭代。

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
idea or another note. The first version supports page navigation; exact text
highlighting and image-region excerpts are future work.

References survive history and exports; archives remap file IDs without losing
page numbers. Shares use scoped attachment copies and retain all existing access
controls. Local reading positions are not published.
