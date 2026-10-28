"""Headless companion layout check only; this is never evidence of ATS integration."""

from pathlib import Path
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import sys
from threading import Thread

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "ui-preview"
OUTPUT.mkdir(parents=True, exist_ok=True)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


class PreviewHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


@contextmanager
def preview_server():
    # The generic skill helper leaves a shell-spawned http.server child alive on Windows.
    # Keep this server in-process, use a free port, and always release it on exit.
    handler = partial(PreviewHandler, directory=str(ROOT / "ui" / "dist"))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


with preview_server() as base_url, sync_playwright() as playwright:
    browser = playwright.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 900, "height": 600}, device_scale_factor=1)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(f"{base_url}/?lang=zh_cn&game=off", wait_until="networkidle")
    page.get_by_role("heading", name="ATS 启动台").wait_for()
    page.screenshot(path=str(OUTPUT / "ats-launcher-preview.png"), full_page=True)
    sections = page.locator(".cp-row[data-section]").evaluate_all(
        "nodes => nodes.map(node => ({section: node.dataset.section, text: node.innerText}))"
    )
    assert [item["section"] for item in sections] == [
        "ats", "screen", "controls", "customize", "accounts", "map", "setup", "about", "support"
    ]
    assert page.get_by_role("button", name="启动 ATS 游戏", exact=True).is_disabled()
    assert page.get_by_role("button", name="诊断与修复", exact=True).is_disabled()
    assert page.get_by_role("button", name="查看日志", exact=True).is_disabled()
    assert page.get_by_text("这是界面预览，尚未连接本机 ATS。", exact=False).is_visible()
    assert page.locator("[data-section=ats]").get_attribute("data-here") is not None
    layout = page.locator("section.ob-words[data-place=page]").evaluate(
        "node => ({width: node.clientWidth, height: node.clientHeight, contentHeight: node.scrollHeight})"
    )
    page.get_by_role("button", name="安全卸载", exact=False).scroll_into_view_if_needed()
    assert page.get_by_role("button", name="安全卸载", exact=False).is_visible()
    page.screenshot(path=str(OUTPUT / "ats-launcher-settings-preview.png"), full_page=True)
    for section in ("setup", "accounts", "controls", "map", "ats"):
        page.locator(f".cp-row[data-section={section}]").click()
        page.wait_for_function(
            "section => document.querySelector(`[data-section=\"${section}\"]`).hasAttribute('data-here')",
            arg=section,
        )
    page.get_by_role("heading", name="ATS 启动台").wait_for()
    assert not errors, errors
    result = {"kind": "browser UI preview only", "viewport": [900, 600], "sections": sections,
              "layout": layout, "pageErrors": errors, "nativeCommandsDisabled": True,
              "gameStarted": False, "realAtsTest": False}
    (OUTPUT / "layout-check.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    browser.close()
