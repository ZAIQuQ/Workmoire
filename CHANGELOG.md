# 更新日志 · Changelog

版本遵循 [Semantic Versioning](https://semver.org/)。发布记录见 [GitHub Releases](https://github.com/ZAIQuQ/Workmoire/releases)。

## [1.9.1] — 2026-10-29

- 优化左上角品牌行：图标改为方形，统一项目名与版本按钮的高度和视觉中心。
- 调整字号、圆角与间距，让版本号贴近项目名，并修复侧边栏内边距溢出；桌面与手机布局保持一致。

见[使用说明](docs/user-guide.md)。

### English

Align the sidebar icon, wordmark and version badge with explicit line heights
and balanced proportions. Keep the version beside the name and within the
sidebar padding on desktop and mobile.

## [1.9.0] — 2026-10-29

### 论文阅读笔记

- 速读改为「一句话看懂 → 核心洞见 → 技术要点」，聚焦问题建模、设计逻辑与方法流程，移除审稿式的证据和局限性段落。
- 识别到完整原文摘要时，在速读前展示中英文对照；原文须匹配上传材料，无法识别则省略。
- 发表、作者团队与研究领域只显示已有信息，省略未知字段、空章节和归类解释。
- 删除正文中的「依据所提供的 PDF」、阅读范围说明和待核实占位；读取进度继续保留在导入界面。
- 保持单次 AI 调用、medium 推理、预览后插入与正常保存流程。

见[使用说明](docs/user-guide.md)。

### English

Generate reading notes focused on insights and technical mechanisms instead of
review-style caveats. Show a source-matched abstract with its translation before
the brief when available. Omit unknown metadata, empty sections, classification
explanations and extraction commentary from the document. Import progress remains
visible in the dialog, and analysis still uses one model call.

## [1.8.2] — 2026-10-29

### 修复行内代码边界输入

- 行内代码开头和末尾不再自动吸收新输入的普通文字；点击开头后可输入空格、中文或其他格式的内容。
- 保留 Cmd/Ctrl+E 切换、代码内部编辑、Tab 段落缩进，以及撤销和保存。
- 在代码边界用方向键退出当前代码输入状态时只切换输入格式，不往文档插入占位空格或隐藏字符。
- 工具栏及时显示当前输入格式；中文输入法组合输入保持原生处理。

见[使用说明](docs/user-guide.md)。

### English

Inline code no longer captures ordinary text typed at its boundaries. Preserve
code content while inserting a plain or styled prefix, including native IME
input. Boundary exits change only the typing mark, without adding spacer text;
the toolbar reflects the current typing format.

## [1.8.1] — 2026-10-29

### 修复 Tab 缩进

- 编辑正文时 Tab / Shift+Tab 调整段落或标题缩进，焦点保留在编辑器中；可对选中的多个段落操作。
- 列表使用嵌套/提升层级；代码块以四个空格缩进，支持整行、多行和反向缩进。
- 表格保留前后单元格导航与末尾新增行；边界处不再意外跳到目录。中文输入法组合输入不受拦截。
- 缩进支持撤销、保存、历史、JSON / 完整归档与分享。普通段落的版式缩进不写成 Markdown 代码块。
- Esc 可把正文焦点交还工具栏，其他控件保留正常键盘导航。「更多」中的缩进操作与快捷键一致。

见[使用说明](docs/user-guide.md)。

### English

Handle Tab in the native editor instead of moving focus to the outline. Indent
paragraphs/headings, nest list items and indent code lines; Shift+Tab reverses the
operation. Preserve table navigation, IME composition, undo and native persistence.
Escape returns keyboard focus to the toolbar.

## [1.8.0] — 2026-10-29

### 更紧凑的编辑空间

- 主工具栏改为单行；窄屏可横向滚动，常用按钮、字体选择和提示保持可用。
- 颜色、插入和更多菜单随按钮定位，避免被横向滚动容器裁切。
- 缩短标题区上下留白和标题信息间距，把更多空间留给正文。
- 底栏仅保留「链接文档」与「上报 Bug」，统一大小、样式和对齐，删除输入与保存快捷键提示。
- 专注模式隐藏底栏；退出后恢复，切换文档或手机目录时仍可正常上报 Bug。

见[使用说明](docs/user-guide.md)。

### English

Use a single toolbar row with horizontal overflow on narrow screens and unclipped
formatting menus. Reduce title spacing and unify the document-link and bug-report
actions in the footer. Focus mode hides the footer while preserving the document,
selection and embedded PDF state.

## [1.7.1] — 2026-10-29

- AI 未能确认作者时，不再把未经用户确认的 PDF 元数据作者写入档案；用户手动确认的作者保留。
- 领域标签测试等待文档真正放入编辑器后再验证，并覆盖延迟返回；输入法测试等待编辑器获得焦点和文字更新，修复云端 CI 的时序问题。

见[使用说明](docs/user-guide.md)。

### English

Discard unconfirmed PDF author metadata when analysis cannot ground it. Preserve
explicit author edits. Verify profile insertion after the asynchronous handoff
finishes, including a delayed response.

## [1.7.0] — 2026-10-29

### 论文档案与领域标签

- 论文导入以手动上传 PDF 为唯一入口，来源链接置于上传区下方且可留空。
- 同一次 AI 分析整理标题、作者、发表情况、作者单位、通讯作者与实验室，并保留聚焦动机与卖点的速读摘要。
- 事实须有已提供 PDF 的原文依据；未知发表状态和团队明确标为待核实，不凭姓名或 arXiv 链接猜测，不重新抓取网页。
- 自动归纳一级、二级研究领域，并在预览中生成 1–2 个默认选中的彩色标签；保存前可取消，正常保存后显示在文档目录。
- 修改标题、作者或补填来源链接会保留已生成的分析，放入编辑器时统一整合；不重复调用 AI。
- 上传与归档导入失败的临时文件在返回错误前完成清理。

见[使用说明](docs/user-guide.md)与[论文导入说明](docs/paper-intake.md)。

### English

A single analysis produces an evidence-grounded paper profile and a concise brief.
Manual PDF upload remains required and the source link optional. Publication,
author, correspondence and lab facts need supporting excerpts; inferred research
fields produce up to two selectable tags. Edits retain the analysis, and tags
persist only with the normal document save.

## [1.6.1] — 2026-10-29

### 手动上传 PDF 与长论文解析修复

- 停用论文链接自动下载和编辑器中的 PDF 链接导入，所有 PDF 由用户手动上传。
- 来源链接仅用于记录出处；只有选定本地 PDF 后才能上传、读取和分析。
- 旧的在线获取接口也已停用，旧页面无法继续触发服务器下载；已有附件、原文链接和文档内容保留。
- 手动上传继续提供实际进度、PDF 预览、AI 分析和预估等待时间。
- 修复长论文达到文字提取上限时被误报为无效 PDF：正常停止读取并标注部分文字，保留预览和分析。
- 文字提取失败时保留上传成功状态，并区分文件无效、加密、超时与一般读取异常。

见[使用说明](docs/user-guide.md)。

### English

PDF intake now requires a manual upload. Source URLs are attribution only; remote
PDF imports and legacy online paper lookup are disabled at the API boundary as
well as in the UI. Existing documents and attachments remain available, with
measured uploads, local extraction and optional AI briefs. Fix stream cancellation
at the text limit so valid long PDFs retain partial evidence instead of failing
as invalid files; extraction errors no longer overwrite successful upload status.

## [1.6.0] — 2026-10-29

### 论文速读与等待进度

- 论文分析默认改为 `medium` 推理，保留 `gpt-6.1-sol`，使用独立速读模板输出约 400–700 字。
- 摘要聚焦一句话结论、动机、核心方法与卖点、关键证据和边界，不再默认展开研究选题和复现计划；预览直接展示摘要，插入文档后摘要位于 PDF 前。
- PDF 直接流式上传，按实际传输字节显示进度和速度估计；上传发送完成与服务器确认分开显示。
- 上传与本地文字提取并行，避免为提取文字把刚上传的 PDF 再下载一次；提取进度按已完成页数显示。
- AI 分析显示已用时间、预估进度与剩余时间区间，使用近期任务实测校准；超过常见耗时会明确提示，结果返回前不会显示 100%。
- 现有文档附件上传也显示实际进度；所有分析仍需手动放入编辑器并保存。

见[进度与估时说明](docs/paper-progress.md)和[使用说明](docs/user-guide.md)。

### English

Paper analysis now uses medium reasoning and a concise, versioned brief template.
Direct uploads expose measured byte progress, while local PDF extraction runs in
parallel without downloading the same file again. AI jobs show explicitly
estimated progress and a remaining-time range calibrated from content-free timing
samples. Only completed results reach 100%; overruns are shown honestly.

## [1.5.0] — 2026-10-29

### 中文输入与 Bug 上报

- 修复中文输入法连续退格后重复字母的问题：组合输入期间不再执行会产生空事务的退格快捷键，保留浏览器原生输入区间。
- 使用真实浏览器组合输入验证 `q'we → q'w → q → 去`，覆盖段落、标题、列表、表格、代码块及清空候选文字。
- 页面右下角新增「上报 Bug」，在新页面填写标题、复现说明并上传、拖入或粘贴截图，不打断当前文档。
- 提交记录保存在私有后台，用户菜单的「Bug 记录」可只读查看；接口不提供修改或删除。
- 记录和截图均要求登录，分享服务无法访问。上传有大小限制，失败可重试，重复请求不会生成重复记录。

见[Bug 上报说明](docs/bug-reports.md)与[使用说明](docs/user-guide.md)。记录和截图随现有定时备份保存。

### English

Fix repeated letters when deleting from a Chinese IME composition by skipping
shortcut handlers until composition finishes. Add a separate bug-report page
with screenshots and reproduction steps, plus an authenticated read-only record
viewer. Reports stay on the private server and are included in regular backups.

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

[1.5.0]: https://github.com/ZAIQuQ/Workmoire/releases/tag/v1.5.0

[1.6.0]: https://github.com/ZAIQuQ/Workmoire/releases/tag/v1.6.0
