"""HTTP transport: POST /rpc (JSON-RPC) and the static browser client at /.

Run from assigns/08/:   python MySolution/server/app.py   -> http://127.0.0.1:8000/
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # MySolution/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flask import Flask, Response, request, send_from_directory  # noqa: E402

from server import rpc, streams  # noqa: E402

STATIC = ROOT / "static"


def create_app(table: streams.StreamTable | None = None) -> Flask:
    app = Flask(__name__, static_folder=None)
    app.config["STREAMS"] = table if table is not None else streams.StreamTable()

    @app.post("/rpc")
    def rpc_endpoint():
        if request.mimetype != "application/json":
            return Response("Content-Type must be application/json\n", 415,
                            mimetype="text/plain")
        status, body = rpc.handle_payload(request.get_data(as_text=True),
                                          app.config["STREAMS"])
        if body is None:
            return Response(status=204)
        return Response(json.dumps(body), status, mimetype="application/json")

    @app.get("/")
    def index():
        return send_from_directory(STATIC, "index.html")

    @app.get("/static/<path:name>")
    def static_file(name):
        return send_from_directory(STATIC, name)

    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    create_app().run(host="127.0.0.1", port=port, threaded=True)
