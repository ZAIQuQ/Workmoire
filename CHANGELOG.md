# 更新日志 · Changelog

版本遵循 [Semantic Versioning](https://semver.org/)。发布记录见 [GitHub Releases](https://github.com/ZAIQuQ/Workmoire/releases)。

## [1.4.0] — 2026-10-29

### 表格宽度

- 表格工具栏新增「每列等宽」，支持普通表格与合并单元格。
- 默认开启「固定宽度」：表格适应正文宽度，长内容换行，拖动列边界只调整相邻列比例。
- 关闭固定宽度后允许向外扩展列宽，超宽表格下方显示可拖动、可键盘操作的横向滚动条。
- 开关、等宽和拖动操作支持撤销/重做，设置随保存、历史、JSON / 完整归档与分享快照保留。
- 窗口变窄时固定表格自动适应，无需修改文档；滚动表格不会导致整个页面横向溢出。

见[使用说明](docs/user-guide.md)。未设置宽度模式的旧表格默认采用固定宽度，原有列宽记录保留。

### English

Tables fit the document width by default. Distribute columns evenly or adjust
adjacent column proportions without expanding the table. Turn off fixed width
to widen columns and use the visible horizontal scrollbar. Merged cells,
undo/redo, narrow screens, native exports and read-only shares retain the layout.

## [1.3.0] — 2026-10-29

### 正文字体与工具栏

- 工具栏新增整篇正文字体选择：无衬线、衬线和等宽，默认字体保持不变。
- 字体随文档保存、历史、草稿、JSON / 完整归档和分享快照保留；支持撤销、重做，切换时不重建内嵌 PDF。
- 文字颜色直接放到工具栏，提供预设色板、自定义颜色与默认颜色恢复，仅作用于选中文字。
- 高亮、行内代码、删除线、对齐、链接和清除格式直接可用；「更多」只保留上下标和列表缩进，菜单不重复常用操作。
- 工具栏图标增加悬停和键盘焦点提示，并显示可用快捷键；窄屏保持工具可访问。
- 新增本地打包的思源宋体作为可选正文样式；代码与公式保留原有字体。

见[使用说明](docs/user-guide.md)。Markdown 导出保留文字；字体和富文本样式请使用 JSON 或完整归档保留。

### English

Choose one font for the entire document and retain it through saves, drafts,
history, native exports and protected shares. Common formatting actions and a
selection color palette now live directly in the toolbar, with hover/focus hints.
The More menu contains only sub/superscript and list indentation. Font changes
support undo/redo without recreating PDF views. All fonts are served locally.

## [1.2.0] — 2026-10-29

### 文档目录

- 正文右侧新增独立目录，编辑、阅读和专注模式下都可使用。
- 自动展示标题 1–6 的层级，点击跳转，随正文滚动高亮当前章节。
- 标题改名、增删、调整层级和撤销后自动更新；重名标题仍可分别定位。
- 窄屏通过「目录」按钮展开，选择章节后自动收起；目录导航不会修改正文或触发保存。
- 保留内嵌 PDF、代码折叠和编辑草稿，支持内容高度变化后的重新定位。

见[使用说明](docs/user-guide.md)。主站和分享服务仍使用原端口与数据目录。

### English

A dedicated right-hand document outline is available while editing, reading and
using focus mode. It follows heading levels 1–6, highlights the current section,
and stays in sync with edits and layout changes. On narrow screens, open it with
the outline button. Navigation preserves the document, selection and embedded PDF.

## [1.1.0] — 2026-10-29

### 新增与改进

- 文档编辑升级为原生富文本：公式、表格、图片、内嵌 PDF、代码高亮与折叠、拖动内容块。
- `/` 插入支持中文、拼音首字母与多词检索，如 `ddm`、`yy cite`、`todo`、`db`。
- 新建入口收敛为空白文档和论文资料；论文支持 PDF、链接或两者同时提供，优先使用上传的 PDF。
- 文档目录直接显示彩色标签，在置顶按钮左侧创建、改名和删除标签。
- 独立的文档分享服务：复杂密码、不可预测链接、可选有效期、撤销和只读快照。
- 新增「关于」、当前版本标记、GitHub 更新检查与更新日志入口。
- 恢复仓库维护与自动化检查，提供中文 / English README 和发布流程。

### 数据与部署

- 保留已有文档、账号、附件和历史；后续编辑不会自动更新已分享的快照。
- 主站默认端口为 `5200`，分享服务为 `5201`。分享需独立配置，见[部署说明](docs/document-sharing.md)。
- Codex 功能可选，生成结果仍需确认、插入和保存；AI 模板的后续优化记录在 [TODO](TODO.md)。

### English

Native rich-text editing, multilingual slash commands, foldable code blocks,
PDF-first paper intake, catalogue bookmarks, password-protected sharing, and an
About dialog with release checks. Existing data remains compatible. Documentation
now has Chinese and English entry points, with restored CI and a repeatable release
workflow. Sharing remains an explicitly published snapshot; later edits stay private.

## Before 1.1.0

Earlier development was published as untagged commits. See the
[commit history](https://github.com/ZAIQuQ/Workmoire/commits/main) for those changes.

[1.1.0]: https://github.com/ZAIQuQ/Workmoire/releases/tag/v1.1.0

[1.2.0]: https://github.com/ZAIQuQ/Workmoire/releases/tag/v1.2.0

[1.3.0]: https://github.com/ZAIQuQ/Workmoire/releases/tag/v1.3.0

[1.4.0]: https://github.com/ZAIQuQ/Workmoire/releases/tag/v1.4.0
