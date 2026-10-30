# 后台自动保存 · Background autosave

自动保存默认开启，无需先手动保存。停笔约 2 秒同步当前文档；连续输入时约每 10 秒也会尝试保存。只有输入了标题、正文或插入内容块的新文档才会自动建立，空白占位不会入库。

## 异常提醒

断网、保存请求失败或其他同步异常时，右上角持续显示原因和 **「建议暂时停止编辑，等待同步恢复」**：

- **网络异常**：断网立即提示；连接失败或请求超时也会提示。网络恢复后自动重试。
- **服务异常**：服务暂时无法保存时保留提醒，按约 2、5、15、30、60 秒退避重试，之后最多每分钟重试一次。
- **登录失效**：暂停写入，提供重新登录入口，提醒恢复本机草稿。
- **版本冲突**：暂停自动覆盖，允许打开最新版本，再合并已保留的草稿。
- **内容无法保存**：显示保存校验原因，修正后可以重试。

继续输入、开始重试或浏览器显示联网，都不会直接清除失败提醒。只有当前改动得到服务器确认，提醒才会消失。没有未保存改动时，重新连通也要经过服务与登录检查。

提醒保留重试和复制当前内容的入口。正常情况下保留本机草稿；浏览器存储也失败时会明确提示复制备份，不会声称草稿已保存。普通、专注和论文阅读台都能看到提醒，提醒会避开已有的草稿恢复与冲突操作。

## 保存行为

- 使用原有版本校验，串行提交请求，保留保存期间继续输入的内容。
- 中文输入法尚未确认或标签修改进行中时等待完成；正文可以在附件上传期间继续同步，附件完成后再同步其引用。
- 保存请求最多等待 30 秒。新建使用稳定请求标识，响应丢失后的重试不会重复创建；如果此前创建的文档已被修改或删除，会提示处理，避免覆盖或重新创建。
- 未插入的 AI 预览、未确认的 PDF 框选不会自动保存。已有分享继续保持主动生成时的快照。
- 连续自动保存约每 5 分钟保留一个历史检查点；有改动的手动保存独立留存，沿用最近 100 个版本的上限。
- 如需手动模式，可以在 **保存** 右侧的设置中暂停自动保存。升级首次采用默认开启策略，之后在当前浏览器选择的暂停状态会保留。

新建请求标识只作为私有运行记录保存，不进入文档导出或分享。私有整库备份保留该记录；删除后的请求记录继续防止迟到重试重新创建文档。

## English

Autosave is on by default for existing and meaningful new documents. It saves
after about two seconds of idle input and also flushes sustained typing roughly
every ten seconds. Empty placeholders are not created.

A persistent notice at the upper right explains network, service, login,
conflict or validation failures and recommends pausing edits. Typing, retrying
or an online event does not dismiss it. Only a confirmed save of the current
changes clears the warning; clean documents verify server/session recovery.
Local draft failures are reported honestly, with a copy action for recovery.

Retries back off to at most once per minute. Requests are serialized and
revision-checked; IME and tag changes are respected, while text can synchronize
during uploads. Stable creation identifiers prevent duplicate documents after
lost responses and reject replay over a modified or deleted document. The
private request ledger is excluded from exports and sharing. Autosave can be
paused from Save settings; shared snapshots remain explicit.
