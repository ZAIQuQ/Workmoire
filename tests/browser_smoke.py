"""Optional real-browser smoke test using synthetic, temporary data only.

Run with a Python environment containing Playwright and its Chromium browser:
    python tests/browser_smoke.py
"""
import sys
import tempfile
import threading
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import workspace_server as app
from playwright.sync_api import sync_playwright, expect


def main():
    with tempfile.TemporaryDirectory(prefix="workmoire-browser-") as temp:
        app.DATA_DIR = Path(temp)
        app.FILES_DIR = app.DATA_DIR / "files"
        app.DB_PATH = app.DATA_DIR / "workspace.db"
        app.SETUP_TOKEN = "synthetic-bootstrap-token"
        app.SESSION_SECRET = "synthetic-browser-secret"
        fake_codex = Path(temp) / "fake_codex.py"
        fake_codex.write_text("import sys\nsys.stdin.read()\nprint('Synthetic assistant output')\n", encoding="utf-8")
        app.CODEX_BIN = sys.executable + " " + str(fake_codex)
        app.init_db()
        server = app.ThreadingHTTPServer(("127.0.0.1", 0), app.WorkspaceHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(viewport={"width": 1440, "height": 1000})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                def accept_dialog(dialog):
                    dialog.accept()

                page.on("dialog", accept_dialog)
                page.goto("http://127.0.0.1:%d" % server.server_port)
                page.locator("#auth-username").fill("browser-tester")
                page.locator("#auth-password").fill("synthetic-browser-password")
                page.locator("#auth-confirm").fill("synthetic-browser-password")
                page.locator("#auth-setup-token").fill(app.SETUP_TOKEN)
                page.locator("#auth-submit").click()
                expect(page.locator("#page-content h1")).to_have_text("总览")
                page.locator('[data-page="review"]').click()
                expect(page.locator("#page-content h1")).to_have_text("今日复盘")
                page.locator('[data-page="dashboard"]').click()
                page.locator('[data-page="note"]').click()
                page.locator("#new-content").click()
                page.locator("#edit-title").fill("Synthetic browser note")
                page.locator("#edit-content").fill("A recoverable thought.")
                page.locator("#save-content").click()
                expect(page.locator("#save-indicator")).to_contain_text("已保存")
                expect(page.locator("#select-all-items")).to_be_visible()
                expect(page.locator("#bulk-actions")).to_be_hidden()
                page.locator("#edit-summary").fill("Synthetic history marker")
                page.locator("#save-content").click()
                expect(page.locator(".history-row")).to_have_count(1)
                page.locator(".restore-revision").first.click()
                expect(page.locator("#save-indicator")).to_contain_text("已恢复历史版本")
                expect(page.locator("#edit-summary")).to_have_value("")
                page.locator("#edit-kind").select_option("project")
                page.locator("#save-content").click()
                expect(page.locator("#page-heading")).to_have_text("项目空间")
                page.locator("#edit-kind").select_option("note")
                page.locator("#save-content").click()
                expect(page.locator("#page-heading")).to_have_text("知识库")
                page.locator("#assistant-content").click()
                page.locator("#assistant-run").click()
                expect(page.locator("#assistant-result")).to_contain_text("Synthetic assistant output")
                page.locator("#assistant-apply-content").click()
                expect(page.locator("#edit-content")).to_have_value("A recoverable thought.\n\nSynthetic assistant output")
                page.locator("#save-content").click()
                expect(page.locator("#save-indicator")).to_contain_text("已保存")
                calendar_response = page.context.request.post(
                    "http://127.0.0.1:%d/api/items" % server.server_port,
                    data={"kind": "project", "title": "Synthetic calendar project", "due_date": date.today().isoformat(), "status": "active"},
                )
                assert calendar_response.status == 201
                page.locator('[data-page="calendar"]').click()
                expect(page.locator("#page-content h1")).to_have_text("计划日历")
                expect(page.locator(".calendar-item")).to_contain_text("Synthetic calendar project")
                page.locator("#global-search-trigger").click()
                page.locator("#global-search").fill("recoverable")
                expect(page.locator(".search-item-result")).to_contain_text("A recoverable thought.")
                page.locator("#global-search-kind").select_option("note")
                expect(page.locator(".search-item-result")).to_have_count(1)
                page.locator("#search-dialog").press("Escape")
                # Create a synthetic project to exercise links across spaces.
                response = page.context.request.post(
                    "http://127.0.0.1:%d/api/items" % server.server_port,
                    data={"kind": "project", "title": "Synthetic linked project"},
                )
                assert response.status == 201
                project_id = response.json()["item"]["id"]
                page.locator('[data-page="note"]').click()
                page.locator(".content-item").click()
                page.locator("#related-target").select_option(str(project_id))
                page.locator("#add-related").click()
                expect(page.locator("#related-list")).to_contain_text("Synthetic linked project")
                page.locator("#related-list .related-link").click()
                expect(page.locator("#edit-title")).to_have_value("Synthetic linked project")
                expect(page.locator("#related-list")).to_contain_text("Synthetic browser note")
                page.locator("#related-list .related-link").click()
                expect(page.locator("#edit-title")).to_have_value("Synthetic browser note")
                page.locator('[data-page="graph"]').click()
                expect(page.locator("#page-content h1")).to_have_text("关系地图")
                expect(page.locator(".graph-node")).to_have_count(3)
                expect(page.locator(".graph-edge")).to_have_count(1)
                page.locator('.graph-node[data-id="%d"]' % project_id).click()
                expect(page.locator("#edit-title")).to_have_value("Synthetic linked project")
                page.locator('[data-page="note"]').click()
                page.locator(".content-item").filter(has_text="Synthetic browser note").click()

                # Same-space navigation must respect unsaved edits.
                page.remove_listener("dialog", accept_dialog)
                def dismiss_dialog(dialog):
                    dialog.dismiss()

                page.on("dialog", dismiss_dialog)
                page.locator("#edit-summary").fill("Unsaved synthetic summary")
                page.locator('[data-page="note"]').click()
                expect(page.locator("#edit-summary")).to_have_value("Unsaved synthetic summary")
                page.remove_listener("dialog", dismiss_dialog)
                page.on("dialog", accept_dialog)
                page.locator("#save-content").click()
                expect(page.locator("#save-indicator")).to_contain_text("已保存")
                page.locator("#related-list .related-remove").click()
                expect(page.locator("#related-list .related-link")).to_have_count(0)
                page.locator("#delete-content").click()
                expect(page.locator(".content-item")).to_have_count(0)
                page.locator('[data-page="trash"]').click()
                expect(page.locator("#trash-items")).to_contain_text("Synthetic browser note")
                page.locator(".restore-item").click()
                expect(page.locator(".restore-item")).to_have_count(0)
                page.locator('[data-page="note"]').click()
                page.locator(".content-item").click()
                expect(page.locator("#edit-content")).to_have_value("A recoverable thought.\n\nSynthetic assistant output")
                task_response = page.context.request.post(
                    "http://127.0.0.1:%d/api/items" % server.server_port,
                    data={"kind": "note", "title": "Synthetic task note", "content": "- [ ] Check the next step\n- [x] Keep the finished step"},
                )
                assert task_response.status == 201
                task_id = task_response.json()["item"]["id"]
                page.locator('[data-page="note"]').click()
                page.get_by_text("Synthetic task note", exact=True).click()
                page.locator('[data-tab="preview"]').click()
                expect(page.locator("#content-preview input[type=checkbox]")).to_have_count(2)
                expect(page.locator("#task-progress")).to_contain_text("1/2")
                page.locator("#content-preview input[type=checkbox]").first.check()
                expect(page.locator("#task-progress")).to_contain_text("2/2")
                expect(page.locator("#edit-content")).to_have_value("- [x] Check the next step\n- [x] Keep the finished step")
                expect(page.locator("#save-indicator")).to_contain_text("任务已更新")
                page.locator("#save-content").click()
                expect(page.locator("#save-indicator")).to_contain_text("已保存")
                task_delete = page.context.request.delete(
                    "http://127.0.0.1:%d/api/items/%d" % (server.server_port, task_id),
                )
                assert task_delete.status == 200
                task_purge = page.context.request.delete(
                    "http://127.0.0.1:%d/api/trash/items/%d" % (server.server_port, task_id),
                )
                assert task_purge.status == 200
                bulk_items = []
                for title in ("Synthetic bulk one", "Synthetic bulk two"):
                    bulk_response = page.context.request.post(
                        "http://127.0.0.1:%d/api/items" % server.server_port,
                        data={"kind": "note", "title": title, "status": "inbox"},
                    )
                    assert bulk_response.status == 201
                    bulk_items.append(bulk_response.json()["item"]["id"])
                page.locator('[data-page="note"]').click()
                for title in ("Synthetic bulk one", "Synthetic bulk two"):
                    page.locator(".content-item").filter(has_text=title).locator("input[type=checkbox]").check()
                expect(page.locator("#bulk-toolbar")).to_be_visible()
                expect(page.locator("#bulk-count")).to_contain_text("2")
                page.locator("#bulk-status").select_option("active")
                page.locator("#bulk-apply-status").click()
                expect(page.locator(".content-item").filter(has_text="Synthetic bulk one").locator(".status-pill")).to_have_class("status-pill active")
                bulk_cleanup = page.context.request.post(
                    "http://127.0.0.1:%d/api/items/bulk" % server.server_port,
                    data={"ids": bulk_items, "action": "trash"},
                )
                assert bulk_cleanup.status == 200
                for bulk_id in bulk_items:
                    bulk_purge = page.context.request.delete(
                        "http://127.0.0.1:%d/api/trash/items/%d" % (server.server_port, bulk_id),
                    )
                    assert bulk_purge.status == 200
                page.locator('[data-page="files"]').click()
                page.locator("#file-input").set_input_files({
                    "name": "synthetic.txt", "mimeType": "text/plain", "buffer": b"file payload",
                })
                expect(page.locator(".file-row")).to_have_count(1)
                page.locator(".file-delete").click()
                expect(page.locator(".file-row")).to_have_count(0)
                page.locator('[data-page="trash"]').click()
                page.locator(".restore-file").click()
                expect(page.locator(".restore-file")).to_have_count(0)
                page.locator('[data-page="files"]').click()
                expect(page.locator(".file-row")).to_contain_text("synthetic.txt")
                page.locator(".file-delete").click()
                expect(page.locator(".file-row")).to_have_count(0)
                page.locator('[data-page="trash"]').click()
                page.locator(".purge-file").click()
                expect(page.locator(".purge-file")).to_have_count(0)
                assert not list(app.FILES_DIR.iterdir()), "purged file bytes still exist"
                pagination_items = []
                for index in range(101):
                    pagination_response = page.context.request.post(
                        "http://127.0.0.1:%d/api/items" % server.server_port,
                        data={"kind": "note", "title": "Synthetic page %03d" % index},
                    )
                    assert pagination_response.status == 201
                    pagination_items.append(pagination_response.json()["item"]["id"])
                page.locator('[data-page="note"]').click()
                expect(page.locator("#load-more-items")).to_be_visible()
                page.locator("#load-more-items").click()
                expect(page.locator("#load-more-items")).to_have_count(0)
                for start in (0, 100):
                    pagination_cleanup = page.context.request.post(
                        "http://127.0.0.1:%d/api/items/bulk" % server.server_port,
                        data={"ids": pagination_items[start:start + 100], "action": "trash"},
                    )
                    assert pagination_cleanup.status == 200
                for pagination_id in pagination_items:
                    pagination_purge = page.context.request.delete(
                        "http://127.0.0.1:%d/api/trash/items/%d" % (server.server_port, pagination_id),
                    )
                    assert pagination_purge.status == 200
                page.reload()
                expect(page.locator("#page-content h1")).to_have_text("总览")
                page.set_viewport_size({"width": 390, "height": 844})
                page.locator("#mobile-menu").click()
                page.locator('[data-page="note"]').click()
                page.locator(".content-item").click()
                page.locator("#delete-content").click()
                expect(page.locator(".content-item")).to_have_count(0)
                page.locator("#mobile-menu").click()
                page.locator('[data-page="trash"]').click()
                page.locator(".purge-item").click()
                expect(page.locator(".purge-item")).to_have_count(0)
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), "mobile overflow"
                assert not errors, errors
                browser.close()
                print("Browser smoke passed: setup, navigation, save, item/file trash, restore, purge, mobile")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)


if __name__ == "__main__":
    main()
