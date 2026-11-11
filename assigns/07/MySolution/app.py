"""HTTP transport: Flask app exposing POST /rpc.

Start (from assigns/07/):   python3 MySolution/app.py      -> http://127.0.0.1:8000/rpc
"""
from __future__ import annotations

import json
import logging

from flask import Flask, Response, request

import rpc


def create_app() -> Flask:
    app = Flask(__name__)

    @app.post("/rpc")
    def rpc_endpoint():
        if request.mimetype != "application/json":
            return Response("Content-Type must be application/json\n", status=415,
                            mimetype="text/plain")
        status, body = rpc.handle_payload(request.get_data(as_text=True))
        if body is None:
            return Response(status=204)
        return Response(json.dumps(body), status=status, mimetype="application/json")

    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    create_app().run(host="127.0.0.1", port=8000)
