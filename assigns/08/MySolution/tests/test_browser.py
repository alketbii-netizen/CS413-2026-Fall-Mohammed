"""Browser tests for the client (required test 10), using Playwright.

Skipped automatically when Playwright or its Chromium is not installed;
TESTING.md has the equivalent manual checklist.
    pip install playwright && python -m playwright install chromium
"""
import logging
import threading
import unittest

from werkzeug.serving import make_server

from server import streams
from server.app import create_app

logging.getLogger("werkzeug").setLevel(logging.ERROR)

try:
    from playwright.sync_api import sync_playwright
    _pw = sync_playwright().start()
    _browser = _pw.chromium.launch()
except Exception as e:  # pragma: no cover - environment dependent
    _browser = None
    SKIP = f"Playwright/Chromium unavailable: {e.__class__.__name__}"


def tearDownModule():
    if _browser is not None:
        _browser.close()
        _pw.stop()


@unittest.skipIf(_browser is None, "Playwright/Chromium not installed")
class BrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table = streams.StreamTable()
        cls.server = make_server("127.0.0.1", 0, create_app(cls.table), threaded=True)
        cls.url = f"http://127.0.0.1:{cls.server.server_port}/"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        self.page = _browser.new_page()
        self.rpc_calls = []
        self.page.on("request", lambda r: r.url.endswith("/rpc") and self.rpc_calls.append(r.post_data))
        self.page.goto(self.url)

    def tearDown(self):
        self.page.close()

    def text(self, sel):
        return self.page.locator(sel).inner_text()

    def test_start_step_reset(self):
        p = self.page
        self.assertTrue(p.locator("#step").is_disabled())
        p.click("#start")
        p.wait_for_function("document.querySelector('#status').textContent.includes('Opened')")
        self.assertEqual(p.locator(".cell").count(), 64)
        p.click("#step")
        p.wait_for_function("document.querySelector('#events').textContent === '1'")
        self.assertIn("try (row 0, col 0)", self.text("#log"))
        self.assertEqual(p.locator(".cell.try").count(), 1)
        p.click("#step")
        p.wait_for_function("document.querySelector('#events').textContent === '2'")
        self.assertEqual(p.locator(".cell.place").count(), 1)
        # incremental: one queens.next so far, asking for a small batch
        nexts = [c for c in self.rpc_calls if "queens.next" in c]
        self.assertEqual(len(nexts), 1)
        self.assertIn('"limit":8', nexts[0])
        p.click("#reset")
        p.wait_for_function("document.querySelector('#events').textContent === '0'")
        self.assertEqual(p.locator(".cell.queen").count(), 0)
        self.assertTrue(p.locator("#step").is_disabled())
        self.assertTrue(any("queens.close" in c for c in self.rpc_calls))

    def test_play_pause_and_speed(self):
        p = self.page
        p.fill("#speed", "10")
        p.click("#start")
        p.wait_for_function("document.querySelector('#status').textContent.includes('Opened')")
        p.click("#play")
        self.assertEqual(self.text("#play"), "Pause")
        p.wait_for_function("Number(document.querySelector('#events').textContent) >= 15")
        p.click("#play")
        self.assertEqual(self.text("#play"), "Play")
        n = int(self.text("#events"))
        p.wait_for_timeout(300)
        self.assertLessEqual(int(self.text("#events")) - n, 1)   # paused
        self.assertGreater(p.locator(".log li.reject").count(), 0)

    def test_next_solution_and_completion_on_4x4(self):
        p = self.page
        p.select_option("#size", "4")
        p.click("#start")
        p.wait_for_function("document.querySelector('#status').textContent.includes('Opened')")
        p.click("#next-solution")
        p.wait_for_function("document.querySelector('#solutions').textContent === '1'")
        self.assertIn("Solution #1", self.text("#status"))
        self.assertIn("solved", p.locator("#board").get_attribute("class"))
        self.assertEqual(p.locator(".cell.queen").count(), 4)
        p.click("#next-solution")
        p.wait_for_function("document.querySelector('#solutions').textContent === '2'")
        p.click("#next-solution")          # no more solutions -> done
        p.wait_for_function("document.querySelector('#status').textContent.includes('Search complete')")
        self.assertEqual(self.text("#start"), "Restart")
        self.assertTrue(p.locator("#step").is_disabled())
        p.click("#start")                  # restart after completion
        p.wait_for_function("document.querySelector('#solutions').textContent === '0'")

    def test_rpc_failure_is_visible(self):
        p = self.page
        p.click("#start")
        p.wait_for_function("document.querySelector('#status').textContent.includes('Opened')")
        p.route("**/rpc", lambda route: route.abort())
        p.click("#step")
        p.wait_for_selector("#error:not([hidden])")
        self.assertIn("RPC failure", self.text("#error"))
        p.unroute("**/rpc")
        p.click("#start")
        p.wait_for_selector("#error", state="hidden")

    def test_expired_stream_error_shown(self):
        p = self.page
        p.click("#start")
        p.wait_for_function("document.querySelector('#status').textContent.includes('Opened')")
        for sid in list(self.table._entries):
            self.table.close(sid)
        p.click("#step")
        p.wait_for_selector("#error:not([hidden])")
        self.assertIn("-32020", self.text("#error"))


if __name__ == "__main__":
    unittest.main()
