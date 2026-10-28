# 更新日志 · Changelog

版本遵循 [Semantic Versioning](https://semver.org/)。发布记录见 [GitHub Releases](https://github.com/ZAIQuQ/Workmoire/releases)。

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
