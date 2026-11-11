"""HTTP-level tests through Flask's test client (run from assigns/07/)."""
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import rpc        # noqa: E402
import service    # noqa: E402
from app import create_app  # noqa: E402

FACT = """let fact : sint -> sint =
  fix fact(n: sint): sint =>
    if n <= 1 then 1 else n * fact(n - 1)
in fact(6) end"""
LAMBDA3 = Path(service.__file__).resolve().parent.parent / "LAMBDA3"


class RpcTests(unittest.TestCase):
    def setUp(self):
        self.c = create_app().test_client()

    def post(self, payload=None, raw=None, ctype="application/json"):
        data = raw if raw is not None else json.dumps(payload)
        r = self.c.post("/rpc", data=data, content_type=ctype)
        return r.status_code, (r.get_json() if r.data else None)

    def call(self, method, params, id_=1):
        return self.post({"jsonrpc": "2.0", "method": method, "params": params, "id": id_})

    def ok(self, resp, id_):
        st, b = resp
        self.assertEqual(st, 200)
        self.assertEqual(b["jsonrpc"], "2.0")
        self.assertEqual(b["id"], id_)
        self.assertNotIn("error", b)
        return b["result"]

    def err(self, resp, id_, code):
        st, b = resp
        self.assertEqual(st, 200)
        self.assertEqual(b["id"], id_)
        self.assertNotIn("result", b)
        self.assertEqual(b["error"]["code"], code)
        self.assertNotIn("Traceback", json.dumps(b))
        return b["error"]

    # 1
    def test_health(self):
        self.assertEqual(self.ok(self.call("service.health", {}, "h1"), "h1"),
                         {"status": "ok", "version": "1.0"})

    # 2
    def test_typecheck(self):
        self.assertEqual(self.ok(self.call("lambda.typecheck", {"source": "1 + 2"}), 1),
                         {"type": "sint"})
        self.assertEqual(self.ok(self.call("lambda.typecheck", {"source": FACT}), 1),
                         {"type": "sint"})

    # 3
    def test_interpret_arithmetic_factorial_tuple_collection(self):
        self.assertEqual(self.ok(self.call("lambda.interpret", {"source": "6 * 7"}, 2), 2),
                         {"type": "sint", "value": "42"})
        self.assertEqual(self.ok(self.call("lambda.interpret", {"source": FACT}, 3), 3),
                         {"type": "sint", "value": "720"})
        r = self.ok(self.call("lambda.interpret", {"source": "(1, true)"}, 4), 4)
        self.assertEqual(r["type"], "(sint, bool)")
        self.assertEqual(r["value"], "(1, true)")
        src = (LAMBDA3 / "mytest" / "collections.lam").read_text()
        r = self.ok(self.call("lambda.interpret", {"source": src}, 5), 5)
        self.assertEqual(r["value"], "(12, 3, false, 12)")

    # 4
    def test_compile_python_and_javascript(self):
        for target in ("python", "javascript"):
            r = self.ok(self.call("lambda.compile", {"source": FACT, "target": target}, target), target)
            self.assertEqual(r["target"], target)
            self.assertIsInstance(r["code"], str)
            self.assertTrue(r["code"].strip())
        self.err(self.call("lambda.compile", {"source": FACT, "target": "c"}), 1, -32602)

    # 5, 9
    def test_syntax_and_type_errors_distinct(self):
        e = self.err(self.call("lambda.typecheck", {"source": "1 +"}, 7), 7, -32010)
        self.assertIn("message", e["data"])
        self.err(self.call("lambda.typecheck", {"source": "1 + true"}, 8), 8, -32011)
        self.err(self.call("lambda.interpret", {"source": "x + 1"}, 9), 9, -32011)   # unbound
        self.err(self.call("lambda.compile", {"source": "(", "target": "python"}, 10), 10, -32010)

    # 6
    def test_invalid_inputs(self):
        self.err(self.post(raw="{bad json"), None, -32700)
        self.err(self.post({"method": "service.health", "id": 1}), None, -32600)
        self.err(self.post({"jsonrpc": "2.0", "method": 5, "id": 1}), None, -32600)
        self.err(self.post({"jsonrpc": "2.0", "method": "x", "id": [1]}), None, -32600)
        self.err(self.post(5), None, -32600)
        self.err(self.call("no.such", {}), 1, -32601)
        self.err(self.call("lambda.typecheck", []), 1, -32602)
        self.err(self.post({"jsonrpc": "2.0", "method": "lambda.typecheck", "id": 2}), 2, -32602)
        self.err(self.call("lambda.typecheck", {"source": 5}), 1, -32602)
        self.err(self.call("lambda.typecheck", {"source": "   "}), 1, -32602)
        big = "1" + " + 1" * service.MAX_SOURCE_CHARS
        self.err(self.call("lambda.typecheck", {"source": big}), 1, -32602)
        st, _ = self.post({"jsonrpc": "2.0", "method": "service.health", "id": 1},
                          ctype="text/plain")
        self.assertEqual(st, 415)

    # 7
    def test_function_value_formatted(self):
        r = self.ok(self.call("lambda.interpret",
                              {"source": "lam (x: sint) => x + 1"}, 11), 11)
        self.assertEqual(r["type"], "sint -> sint")
        self.assertEqual(r["value"], "<lam>")
        self.assertNotIn("ENV", json.dumps(r))

    # 8
    def test_injected_failure_and_timeout(self):
        with mock.patch.object(service, "typecheck", side_effect=RuntimeError("/secret/path")):
            e = self.err(self.call("lambda.typecheck", {"source": "1"}, "f1"), "f1", -32603)
            self.assertNotIn("secret", json.dumps(e))
        with mock.patch.object(service, "interpret",
                               side_effect=service.ServiceTimeout("t")):
            self.err(self.call("lambda.interpret", {"source": "1"}, "t1"), "t1", -32012)

    def test_real_timeout_terminates_worker(self):
        # A deadline shorter than the worker can finish forces termination.
        with mock.patch.object(service, "INTERPRET_TIMEOUT", 0.001):
            self.err(self.call("lambda.interpret", {"source": FACT}, "slow"), "slow", -32012)

    # 10
    def test_batches_and_notifications(self):
        st, b = self.post([
            {"jsonrpc": "2.0", "method": "service.health", "params": {}, "id": "a"},
            {"jsonrpc": "2.0", "method": "service.health", "params": {}},
            {"jsonrpc": "2.0", "method": "lambda.typecheck", "params": {"source": "1"}, "id": 2},
            {"foo": "bar"},
        ])
        self.assertEqual(st, 200)
        self.assertEqual(len(b), 3)
        by_id = {r["id"]: r for r in b if r["id"] is not None}
        self.assertEqual(by_id["a"]["result"]["status"], "ok")
        self.assertEqual(by_id[2]["result"]["type"], "sint")
        self.assertEqual([r["error"]["code"] for r in b if r["id"] is None], [-32600])
        st, b = self.post([{"jsonrpc": "2.0", "method": "service.health", "params": {}}])
        self.assertEqual((st, b), (204, None))
        st, b = self.post([])
        self.assertEqual(st, 200)
        self.assertEqual(b["error"]["code"], -32600)
        self.assertIsNone(b["id"])
        st, b = self.post({"jsonrpc": "2.0", "method": "service.health", "params": {}})
        self.assertEqual((st, b), (204, None))


if __name__ == "__main__":
    unittest.main()
