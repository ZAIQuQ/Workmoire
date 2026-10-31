# 更新日志 · Changelog

版本遵循 [Semantic Versioning](https://semver.org/)。发布记录见 [GitHub Releases](https://github.com/ZAIQuQ/Workmoire/releases)。

## [1.15.11] — 2026-10-31

- 历史版本预览进一步显示具体格式变化类型，例如字体前后值、行间距、标题层级、文字格式/颜色、段落对齐/缩进、表格宽度和代码折叠状态。

见[使用说明](docs/user-guide.md)。

### English

- History previews now identify specific rich-format changes, including font values, line spacing, heading levels, text styles/colors, paragraph alignment/indentation, table width, and code-fold state.

## [1.15.10] — 2026-10-31

- 历史版本预览现在会识别并提示仅富文本格式或内容块属性发生的变化，行间距、字体、文字样式、表格属性等改动不再显示成空的正文差异。

见[使用说明](docs/user-guide.md)。

### English

- History previews now report rich-text formatting and block-attribute changes even when the Markdown line diff is unchanged, covering line spacing, fonts, text styles, and table attributes.

## [1.15.9] — 2026-10-31

- 修复专注模式下点击右侧目录标题后目录自动收起的问题；桌面专注模式会保持目录展开并继续阅读，窄屏目录仍在跳转后收起以避免遮挡正文。

见[使用说明](docs/user-guide.md)。

### English

- Keep the desktop focus-mode outline open after navigating to a heading. Compact phone outlines still close after navigation so they do not cover the document.

## [1.15.8] — 2026-10-31

- 每个正文和标题块左侧的块操作手柄增加段落样式选择，可直接切换正文与标题 1–6，并支持标题升降级。
- 段落样式切换进入撤销、保存、历史、目录和分享链路，保留原有正文内容与段落格式。

见[使用说明](docs/user-guide.md)。

### English

- Add a paragraph-style selector to every body and heading block handle, allowing direct conversion between body text and heading levels 1–6.
- Style changes participate in undo, save, history, outline, and sharing while preserving the block content and existing paragraph formatting.

## [1.15.7] — 2026-10-31

- 修复 LaTeX 块将没有 Markdown 标记的英文段落误判为整块数学公式的问题；纯文本回复现在按段落预览，保留空格、换行和正常字体。
- 保留明确 TeX 命令、环境和公式结构的 KaTeX 渲染，并继续支持 OpenReview 风格的 Markdown、表格、行内公式和代码块。

见[使用说明](docs/user-guide.md)。

### English

- Fix LaTeX blocks misclassifying plain English paragraphs without Markdown markers as one large math expression. Prose now previews with normal spacing, paragraphs, and text faces.
- Keep KaTeX for clear TeX commands, environments, and equation structure while retaining Markdown, tables, inline math, and code-fence support for OpenReview-style replies.

## [1.15.6] — 2026-10-31

- 修复颜色工具栏在打开菜单或自定义取色器后丢失正文选区的问题；预设色、自定义色和恢复默认颜色都会作用于原选中文字。
- 工具栏增加统一行间距，可对当前段落或选中的段落/标题设置默认、1.0、1.15、1.5、1.75 和 2.0，并随原生文档、历史、导入导出和分享保存。
- 字体选择改用更直观的本地字体名称，增加系统默认与 Inter，并保留 Noto Sans SC、Noto Serif SC 和 Maple Mono；代码、公式和 PDF 字体继续独立。

见[使用说明](docs/user-guide.md)。

### English

- Preserve the selected text when opening the color menu or native color picker, so preset, custom, and reset colors apply to the intended selection.
- Add paragraph line-spacing controls for default, 1.0, 1.15, 1.5, 1.75, and 2.0, preserved through native documents, history, imports/exports, and sharing.
- Replace abstract font labels with local font names, add System Default and Inter, and keep Noto Sans SC, Noto Serif SC, and Maple Mono available while code, math, and PDF faces remain independent.

## [1.15.5] — 2026-10-30

- 为版本说明补充统一的「使用说明」入口，保证 About 面板在每个发布版本中都能直接跳转用户指南。
- 分享页 LaTeX 块保留只读 Write 标签和「复制 LaTeX」按钮，接收者可以复制原始源码。
- LaTeX Preview 识别 Markdown 表格、行内公式、粗体和代码围栏，OpenReview 回复可以直接预览。

见[使用说明](docs/user-guide.md)与[后台自动保存](docs/autosave.md)。

### English

Shared LaTeX blocks keep a read-only Write tab with a Copy LaTeX action.
Preview detects OpenReview-style Markdown prose, tables, inline math and fenced
code and uses the safe local Markdown renderer instead of producing a blank view.

## [1.15.4] — 2026-10-30

- 修正创建请求响应丢失后的自动保存重放：客户端会立即把响应期间继续输入的正文补写到已去重文档。

见[后台自动保存](docs/autosave.md)。

### English

After an uncertain automatic creation response, immediately replay the latest
local edits against the deduplicated document so input made during recovery is
not delayed or lost.

## [1.15.3] — 2026-10-30

- 分享页 LaTeX 块保留只读 Write 标签和「复制 LaTeX」按钮，接收者可以复制原始源码。
- LaTeX Preview 现在识别 Markdown 表格、行内公式、粗体和代码围栏，OpenReview 回复可以直接预览。
- LaTeX Preview 兼容 OpenReview 风格的 Markdown 正文、加粗和 fenced code；检测到这类内容时使用安全 Markdown 预览，不再交给 KaTeX 造成空白或异常。

见[使用说明](docs/user-guide.md)。

### English

Shared LaTeX blocks keep a read-only Write tab with a Copy LaTeX action.
Preview detects OpenReview-style Markdown prose and fenced code and uses the
safe local Markdown renderer instead of producing a blank or invalid TeX view.

## [1.15.2] — 2026-10-30

- 已生成的分享链接现在会随文档的每次已保存改动自动更新，链接、密码、有效期和密码保护状态保持不变；未保存草稿不会公开。
- 分享弹窗明确显示当前链接是否已同步到最新保存版本。
- 分享阅读页目录固定在正文右侧，长文阅读时保持可见；手机端继续使用可展开目录。

见[分享说明](docs/document-sharing.md)。

### English

Keep generated share URLs live across later saved edits. Preserve URL, password,
expiry and protection mode while replacing the published document and scoped
attachments in place; unsaved drafts remain private. The owner dialog shows
whether the link is current.

## [1.15.1] — 2026-10-30

- 自动保存永久开启，移除保存按钮下的开关；已有文档和有实际内容的新文档统一后台同步，停笔约 3 秒保存。
- 每次有实际改动的自动保存或手动保存都会生成历史版本；无变化不会重复记录。
- 历史版本面板增加正文新增/删除行预览、保存时间和指定版本恢复入口。

见[使用说明](docs/user-guide.md)与[后台自动保存](docs/autosave.md)。

### English

Make autosave permanently enabled and remove its toggle. Existing and meaningful
new documents sync in the background after about three seconds of idle input.
Every changed automatic or manual save creates a restorable history version;
unchanged saves create none. History now previews line changes and provides a
version restore action.

## [1.15.1] — 2026-10-30

- 自动保存永久开启，移除保存按钮下的开关；已有文档和有实际内容的新文档统一后台同步，停笔约 3 秒保存。
- 每次有实际改动的自动保存或手动保存都会生成历史版本；无变化不会重复记录。
- 历史版本面板增加正文新增/删除行预览、保存时间和指定版本恢复入口。

见[后台自动保存](docs/autosave.md)。

### English

Make autosave permanently enabled and remove its toggle. Existing and meaningful
new documents sync in the background after about three seconds of idle input.
Every changed automatic or manual save creates a restorable history version;
unchanged saves create none. History previews line changes and provides restore.

## [1.15.0] — 2026-10-30

- 输入 `/latex` 插入米色 LaTeX 块，提供 Write / Preview 标签、字符数、TeX is supported 提示和受控 TeX/KaTeX 预览；正常、阅读和分享模式保留对应只读状态。
- 专注模式下右侧目录增宽到 280px，长标题更少换行，并新增目录收起/展开入口；退出专注模式后恢复普通目录布局。
- 分享阅读页增加右侧只读目录，手机端可切换显示；目录跟随标题更新并支持点击定位。
- 修复自动保存版本校验中标题节点级别丢失导致的“保存后仍未保存”状态。
- 自动保存不再提供关闭开关，停笔约 3 秒固定同步；每次有实际改动的自动/手动保存都生成可查看、可回退历史。

见[使用说明](docs/user-guide.md)与[阅读台指南](docs/reading-desk.md)。

### English

Add a warm Overleaf-like `/latex` block with Write / Preview, character count,
TeX support copy and controlled TeX/KaTeX rendering. Widen and collapse the
focus-mode outline, and add a read-only outline to shared readers with a mobile
toggle. Preserve heading levels during rich-document validation so successful
saves do not remain dirty.

## [1.14.1] — 2026-10-30

- 调整离线恢复回归测试，等待实际草稿写入完成后再验证内容，适配即时离线提醒与防抖保存各自的时序。
- 保持 v1.14.0 的默认后台保存与持续异常提醒，离线输入继续避免逐键序列化全文。

见[使用说明](docs/user-guide.md)与[后台自动保存](docs/autosave.md)。

### English

Verify actual local-draft persistence independently of immediate offline
feedback. Preserve default background saving, persistent failure notices and
debounced serialization during offline typing.

## [1.14.0] — 2026-10-30

- 自动保存默认开启：新文档输入内容后也会自动建立，停笔约 2 秒同步，连续输入约每 10 秒保存一次；空白占位不入库。
- 同步异常在右上角持续显示，区分网络、服务、登录、冲突与内容校验，并明确建议暂时停止编辑。
- 输入和重试不会清除失败提醒；只有当前内容确认同步成功后才消失。网络恢复后继续重试，服务故障退避至最多每分钟一次。
- 保留本机草稿与复制入口；草稿也失败时准确提示。正文可在附件上传期间继续同步，提醒不遮挡草稿恢复和冲突操作。
- 新建请求去重，避免响应丢失后的重复文档；已有修改或删除的创建请求会进入冲突处理，保留当前草稿。

见[使用说明](docs/user-guide.md)与[后台自动保存](docs/autosave.md)。

### English

Enable background autosave by default, including meaningful new documents.
Keep actionable sync-failure notices visible until current changes are confirmed
saved, distinguish failure causes, and retry transient outages with capped
backoff. Preserve drafts, continue text sync during uploads, and use idempotent
creation requests without overwriting newer or deleted notes.

## [1.13.0] — 2026-10-30

- 补齐 PDF 焦点下的保存、查找、Esc 和 Ctrl/Cmd+Shift+Enter 原文/笔记切换。
- 新文字引用保留选区和 PDF 指纹，点击后精确定位并短暂高亮；旧页码引用保持可用，指纹不符时提示核对。
- 新增图表与公式框选，确认后上传清晰 PNG，与来源引用一起插入和撤销；取消不创建附件，上传期间保留输入与光标。
- 新增可选自动保存，默认关闭；首次手动保存后，停笔约 2 秒保存。支持有界重试、断网恢复、输入法等待和版本冲突暂停。
- 自动保存合并约 5 分钟内的历史检查点，有变化的手动保存独立留存；已分享快照不会随自动保存更新。
- 精确引用和截图支持历史、导出、归档与分享，继续使用受控附件副本和现有访问权限。

见[使用说明](docs/user-guide.md)、[阅读台](docs/reading-desk.md)、[自动保存](docs/autosave.md)及[后续待办](docs/iteration-backlog.md)。

### English

Add PDF-focused keyboard navigation, fingerprint-checked source highlights and
confirmed image-region excerpts. Introduce opt-in autosave with first-save
control, bounded retries, IME/upload waits, conflict pauses and coalesced history.
Preserve in-flight edits and keep published snapshots unchanged. Citations and
captured figures retain their source through archives and scoped sharing.

## [1.12.0] — 2026-10-29

- 新增论文阅读台：PDF 与现有富文本笔记并排，支持拖动或键盘调整栏宽；手机通过「原文 / 笔记」切换。
- 本机记住附件页码、缩放和笔记阅读位置；阅读台与普通内嵌 PDF 分别保存位置，切换布局保留草稿、选区和阅读器实例。
- 选中 PDF 原文后可「引用到笔记」或「复制引用」。引用带来源和页码，点击可回到原文页面，正常保存后持久化。
- 页码引用支持历史、Markdown、完整归档和文档分享；分享链接使用独立附件副本并遵守密码、有效期与撤销设置。
- 多附件可切换，外部来源继续要求手动上传；首版实现页码定位，精确高亮和图片框选留待后续。

见[使用说明](docs/user-guide.md)与[阅读台指南](docs/reading-desk.md)。

### English

Add a resizable PDF-and-notes reading desk with mobile Original / Notes tabs
and local reading positions. Quote PDF selections into unsaved rich notes,
copy attributed Markdown, and navigate citations back to their source page.
Preserve references through history, archives and protected or direct shares,
using only uploaded PDFs and scoped publication attachments.

## [1.11.1] — 2026-10-29

- 修正目录撤销回归测试的初始化方式，避免快速执行时将测试全文插入与标题修改合并为一次撤销。
- 延续 v1.11.0 的可选密码分享功能，完成发布回归验证。

见[使用说明](docs/user-guide.md)与[分享说明](docs/document-sharing.md)。

### English

Load the saved outline fixture before testing heading undo, preventing fast CI
runs from grouping fixture insertion with the edit. Optional share protection
from v1.11.0 remains available.

## [1.11.0] — 2026-10-29

- 分享弹窗新增「密码保护」开关，默认开启；关闭后，接收者可直接通过链接阅读正文、PDF 和图片。
- 无密码分享隐藏密码栏，复制内容仅含链接；开启保护时仍使用 16 位大小写字母和数字密码，复制内容保留链接与密码两行。
- 已有分享可直接切换保护状态，保留原链接；重新开启保护会生成新密码并使旧访问会话失效。
- 已有分享升级后保持密码保护，原链接和密码不变；两种模式均支持有效期、撤销和回收站联动。

见[使用说明](docs/user-guide.md)与[分享说明](docs/document-sharing.md)。

### English

Add optional password protection to document shares. Protection stays on by
default and for existing shares. Turn it off for direct access to the snapshot
and included media; copying then returns only the URL. Re-enabling protection
keeps the URL, creates a fresh password and invalidates earlier sessions.
Expiry, revocation and trash handling apply in both modes.

## [1.10.2] — 2026-10-29

- 左上角改为上下布局：图标与项目名独占第一行，版本入口位于名称下方并左对齐。
- 项目名完整显示，不再因版本号增长而被挤成省略号；版本号保持可点击，较长版本可独立换行。
- 统一桌面与手机侧栏的品牌间距，保留键盘焦点和更新日志入口。

见[使用说明](docs/user-guide.md)。

### English

Stack the version link beneath the sidebar wordmark with aligned text edges.
Keep the full project name visible independently of version length; long
versions wrap within their own row. Preserve About, release links and keyboard access.

## [1.10.1] — 2026-10-29

- 「复制链接和密码」仅复制链接与密码两行，不再附带有效期说明；永久分享也不再显示重复的说明文字。
- 新建或重置分享密码时生成 16 位数字、大小写字母组合，不含符号，并保证三类字符均存在。
- 已有分享链接和旧密码保持兼容；修改有效期不会改变密码，主动重置后使用新格式。

见[使用说明](docs/user-guide.md)与[分享说明](docs/document-sharing.md)。

### English

Copy only the share link and password. New and reset passwords use sixteen
alphanumeric characters with uppercase, lowercase and digits. Existing links
and legacy passwords remain valid until an explicit reset or regeneration.

## [1.10.0] — 2026-10-29

### 专注正文

- 专注模式将文档名、保存状态、编辑/阅读切换和退出入口合并到 44px 顶栏，收起大标题、字数与更新时间。
- 编辑工具栏默认收起，可通过顶栏「工具栏」随时展开；阅读模式进一步隐藏编辑操作，存在未保存改动时仍保留保存入口。
- 保留右侧目录，收起分享、整理、文档信息面板和底栏；正文更靠近页面顶部。
- 标题仍可编辑，切换专注或读写模式时保留草稿、选区、阅读位置和原 PDF 实例及缩放状态。
- 菜单展开时 Esc 先关闭菜单，再次按 Esc 退出专注；手机端保留可见的退出与目录入口。

见[使用说明](docs/user-guide.md)。

### English

Focus mode uses a compact 44px header and keeps the document body near the top.
Reveal formatting tools on demand; reading mode hides editing controls while
retaining Save for unsaved changes. Reuse existing title, mode and outline controls
without rebuilding document or PDF nodes, and preserve editing and reading state.

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
