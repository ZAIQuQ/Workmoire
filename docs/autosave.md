# 可选自动保存 · Optional autosave

点击 **保存** 右侧的箭头，开启 **自动保存**。设置默认关闭，保存在当前浏览器；同源标签页同步开关状态。

- 新文档第一次仍需手动保存；之后停笔约 2 秒自动保存已有文档。
- 使用原有保存接口、版本校验和草稿机制。保存过程中继续输入的内容会保留，随后再保存。
- 中文输入法尚未确认、附件上传或标签维护进行中时等待完成。
- 临时网络或服务错误会重试最多 3 次，间隔约 2、5、15 秒；仍失败时显示「保存失败」，可点击「重试」。已有文档的保存请求最多等待 30 秒。
- 离线时保留本机草稿，重新联网后继续保存。草稿存储失败会明确显示，不会声称已保存。
- 遇到其他窗口更新、登录失效或无效内容时暂停自动保存。版本冲突需要先处理，继续输入不会覆盖服务端新版本。
- 未插入的 AI 预览、未确认的 PDF 框选不属于文档修改，不会被自动保存。分享仍是主动生成的快照，后续自动保存不会更新已经分享的内容。

连续自动保存约每 5 分钟保留一个历史检查点；有改动的手动保存独立保留历史。服务重启或发生其他版本更新后，会保守地创建新的检查点。当前正文仍在每次成功保存后持久化，历史沿用最近 100 个版本的上限。

## English

Open the arrow beside **保存** and enable **自动保存**. It is off by default and
remembered in the current browser. New documents require their first explicit
save; existing documents save after about two seconds of idle input.

Autosave uses normal revision checks and local drafts, waits for composition and
uploads, and preserves edits made during a pending request. Temporary failures
retry at bounded intervals; conflicts pause instead of overwriting a newer
version. Reconnection resumes offline drafts. Uninserted AI previews and
unconfirmed PDF regions are never saved. Existing shares remain unchanged.

Consecutive automatic saves coalesce history checkpoints over five minutes;
changed manual saves retain independent history. Current document contents are
persisted on each successful save, with the existing 100-revision history limit.
