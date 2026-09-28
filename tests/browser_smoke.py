"""Optional real-browser smoke test using synthetic, temporary data only.

Run with a Python environment containing Playwright and its Chromium browser:
    python tests/browser_smoke.py
"""
import sys
import tempfile
import threading
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
        app.CODEX_BIN = ""
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
                page.on("dialog", lambda dialog: dialog.accept())
                page.goto("http://127.0.0.1:%d" % server.server_port)
                page.locator("#auth-username").fill("browser-tester")
                page.locator("#auth-password").fill("synthetic-browser-password")
                page.locator("#auth-confirm").fill("synthetic-browser-password")
                page.locator("#auth-setup-token").fill(app.SETUP_TOKEN)
                page.locator("#auth-submit").click()
                expect(page.locator("#page-content h1")).to_have_text("总览")
                page.locator('[data-page="note"]').click()
                page.locator("#new-content").click()
                page.locator("#edit-title").fill("Synthetic browser note")
                page.locator("#edit-content").fill("A recoverable thought.")
                page.locator("#save-content").click()
                expect(page.locator("#save-indicator")).to_contain_text("已保存")
                page.locator("#delete-content").click()
                expect(page.locator(".content-item")).to_have_count(0)
                page.locator('[data-page="trash"]').click()
                expect(page.locator("#trash-items")).to_contain_text("Synthetic browser note")
                page.locator(".restore-item").click()
                expect(page.locator(".restore-item")).to_have_count(0)
                page.locator('[data-page="note"]').click()
                page.locator(".content-item").click()
                expect(page.locator("#edit-content")).to_have_value("A recoverable thought.")
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
