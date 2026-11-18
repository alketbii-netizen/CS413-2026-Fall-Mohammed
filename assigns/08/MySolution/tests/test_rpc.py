"""HTTP/JSON-RPC tests through Flask's test client (required tests 6-9)."""
import json
import unittest
from unittest import mock

from server import streams
from server.app import create_app
from solver import queens


class RpcTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(streams.StreamTable())
        self.c = self.app.test_client()

    def post(self, payload=None, raw=None, ctype="application/json"):
        r = self.c.post("/rpc", data=raw if raw is not None else json.dumps(payload),
                        content_type=ctype)
        return r.status_code, (r.get_json() if r.data else None)

    def call(self, method, params, id_=1):
        return self.post({"jsonrpc": "2.0", "method": method, "params": params, "id": id_})

    def ok(self, resp, id_):
        st, b = resp
        self.assertEqual(st, 200)
        self.assertEqual((b["jsonrpc"], b["id"]), ("2.0", id_))
        self.assertNotIn("error", b)
        return b["result"]

    def err(self, resp, id_, code):
        st, b = resp
        self.assertEqual(st, 200)
        self.assertEqual(b["id"], id_)
        self.assertNotIn("result", b)
        self.assertEqual(b["error"]["code"], code)
        text = json.dumps(b)
        for leak in ("Traceback", "/", "D0V", "<lam>", "<fix>", "lazy"):
            if leak == "/" and b["error"].get("data", {}).get("stream_id"):
                continue
            self.assertNotIn(leak, text)
        return b["error"]

    def open(self, size=8, id_="o"):
        return self.ok(self.call("queens.open", {"size": size}, id_), id_)["stream_id"]

    # --- health / ids -----------------------------------------------------
    def test_health_preserves_ids(self):
        for rid in (7, "abc", None, 2.5):
            self.assertEqual(self.ok(self.call("service.health", {}, rid), rid),
                             {"status": "ok", "version": "1.0"})

    # --- open does not force ---------------------------------------------
    def test_open_does_not_force(self):
        r = self.ok(self.call("queens.open", {"size": 8}, 1), 1)
        self.assertEqual(r["size"], 8)
        entry = self.app.config["STREAMS"]._entries[r["stream_id"]]
        self.assertFalse(queens.is_forced(entry.stream))

    # --- limits -------------------------------------------------------------
    def test_limits_1_and_32(self):
        sid = self.open()
        r = self.ok(self.call("queens.next", {"stream_id": sid, "limit": 1}, 2), 2)
        self.assertEqual(len(r["events"]), 1)
        self.assertEqual(r["events"][0], {"event": "try", "column": 0, "row": 0, "board": []})
        self.assertFalse(r["done"])
        r = self.ok(self.call("queens.next", {"stream_id": sid, "limit": 32}, 3), 3)
        self.assertEqual(len(r["events"]), 32)
        entry = self.app.config["STREAMS"]._entries[sid]
        self.assertFalse(queens.is_forced(entry.stream))   # nothing past event 33

    # --- full 8x8 over HTTP (required test 9) ------------------------------
    def test_full_8x8_flow(self):
        sid = self.open()
        sols, last, done, calls = [], None, False, 0
        while not done:
            calls += 1
            r = self.ok(self.call("queens.next", {"stream_id": sid, "limit": 32}, calls), calls)
            self.assertLessEqual(len(r["events"]), 32)
            sols += [tuple(e["board"]) for e in r["events"] if e["event"] == "solution"]
            last = r["events"][-1] if r["events"] else last
            done = r["done"]
        self.assertEqual(len(sols), 92)
        self.assertEqual(len(set(sols)), 92)
        self.assertEqual(last, {"event": "done"})
        r = self.ok(self.call("queens.next", {"stream_id": sid, "limit": 5}, "again"), "again")
        self.assertEqual(r, {"events": [], "done": True})
        self.assertEqual(self.ok(self.call("queens.close", {"stream_id": sid}, "c"), "c"),
                         {"closed": True})
        self.err(self.call("queens.next", {"stream_id": sid, "limit": 1}, "x"), "x", -32020)

    # --- application errors ------------------------------------------------
    def test_unknown_and_closed_stream(self):
        self.err(self.call("queens.next", {"stream_id": "00000000-0000-4000-8000-000000000000",
                                           "limit": 1}, 1), 1, -32020)
        self.err(self.call("queens.next", {"stream_id": "not-a-uuid", "limit": 1}, 2), 2, -32020)
        sid = self.open()
        self.ok(self.call("queens.close", {"stream_id": sid}, 3), 3)
        self.err(self.call("queens.close", {"stream_id": sid}, 4), 4, -32020)

    def test_expired_stream(self):
        clock = [0.0]
        app = create_app(streams.StreamTable(clock=lambda: clock[0], ttl=10))
        c = app.test_client()
        body = lambda m, p, i: json.dumps({"jsonrpc": "2.0", "method": m, "params": p, "id": i})
        sid = c.post("/rpc", data=body("queens.open", {"size": 4}, 1),
                     content_type="application/json").get_json()["result"]["stream_id"]
        clock[0] = 11
        r = c.post("/rpc", data=body("queens.next", {"stream_id": sid, "limit": 1}, 2),
                   content_type="application/json").get_json()
        self.assertEqual((r["id"], r["error"]["code"]), (2, -32020))

    # --- envelopes / validation (required test 7) ---------------------------
    def test_malformed_and_invalid_envelopes(self):
        self.err(self.post(raw="{nope"), None, -32700)
        self.err(self.post({"method": "service.health", "id": 1}), None, -32600)
        self.err(self.post({"jsonrpc": "1.0", "method": "service.health", "id": 1}), None, -32600)
        self.err(self.post({"jsonrpc": "2.0", "method": 3, "id": 1}), None, -32600)
        self.err(self.post({"jsonrpc": "2.0", "method": "service.health", "id": {}}), None, -32600)
        self.err(self.post({"jsonrpc": "2.0", "method": "service.health", "id": True}), None, -32600)
        self.err(self.post("hello"), None, -32600)
        e = self.err(self.post([{"jsonrpc": "2.0", "method": "service.health", "id": 1}]), None, -32600)
        self.assertIn("batch", e["data"]["reason"])
        st, _ = self.post({"jsonrpc": "2.0", "method": "service.health", "id": 1}, ctype="text/plain")
        self.assertEqual(st, 415)

    def test_unknown_method_and_no_eval(self):
        self.err(self.call("queens.solve_all", {}, 1), 1, -32601)
        self.err(self.call("lambda.interpret", {"source": "1"}, 2), 2, -32601)
        self.err(self.call("__import__", {}, 3), 3, -32601)

    def test_invalid_params(self):
        for p in ({}, {"size": 3}, {"size": 11}, {"size": "8"}, {"size": 8.0},
                  {"size": True}, {"size": 8, "extra": 1}):
            self.err(self.call("queens.open", p, "p"), "p", -32602)
        self.err(self.call("queens.open", [8], "q"), "q", -32602)
        self.err(self.call("service.health", {"x": 1}, "h"), "h", -32602)
        sid = self.open()
        for p in ({"stream_id": sid}, {"stream_id": sid, "limit": 0},
                  {"stream_id": sid, "limit": 33}, {"stream_id": sid, "limit": 1.5},
                  {"stream_id": sid, "limit": True}, {"limit": 1}, {"stream_id": 5, "limit": 1}):
            self.err(self.call("queens.next", p, "n"), "n", -32602)
        self.err(self.call("queens.close", {}, "c"), "c", -32602)
        # validation happens before allocation
        before = len(self.app.config["STREAMS"])
        self.call("queens.open", {"size": 99}, 1)
        self.assertEqual(len(self.app.config["STREAMS"]), before)

    def test_notifications(self):
        st, b = self.post({"jsonrpc": "2.0", "method": "service.health", "params": {}})
        self.assertEqual((st, b), (204, None))
        st, b = self.post({"jsonrpc": "2.0", "method": "no.such"})     # still silent
        self.assertEqual((st, b), (204, None))
        sid = self.open()
        st, b = self.post({"jsonrpc": "2.0", "method": "queens.next",
                           "params": {"stream_id": sid, "limit": 3}})
        self.assertEqual((st, b), (204, None))
        r = self.ok(self.call("queens.next", {"stream_id": sid, "limit": 1}, 9), 9)
        self.assertEqual(r["events"][0]["event"], "reject")   # 4th event: the notification consumed 3

    def test_injected_internal_failure(self):
        sid = self.open()
        with self.assertLogs("queens_rpc", "ERROR"), mock.patch.object(queens, "next_event",
                               side_effect=RuntimeError("C:\\secret\\lambda3.py boom")):
            e = self.err(self.call("queens.next", {"stream_id": sid, "limit": 1}, "f"), "f", -32603)
        self.assertNotIn("secret", json.dumps(e))

    def test_static_client_served(self):
        r = self.c.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Next solution", r.data)
        js = self.c.get("/static/main.js")
        self.assertEqual(js.status_code, 200)
        js.close()
        r.close()


if __name__ == "__main__":
    unittest.main()
