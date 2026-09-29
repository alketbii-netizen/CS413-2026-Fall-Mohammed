"""
Entry point: `python run.py`

Binds to the loopback interface only (127.0.0.1) — per Assign04.md,
"Bind a local server to the loopback interface; public hosting is
outside scope." This is a local, single-user application; there is no
authentication and it should never be exposed beyond localhost.
"""

from lambdaweb import create_app

if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=5000, debug=False)
