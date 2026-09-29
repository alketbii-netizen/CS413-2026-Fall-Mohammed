"""
Application factory. Keeping app creation as a factory (rather than a
bare module-level Flask app) is what makes it possible for
tests/test_controller.py to build the app with a *fake* backend, while
reusing the exact same routes and templates as production (Assign04.md:
"At least one controller test must substitute a test backend without
changing view code").
"""

from __future__ import annotations

from flask import Flask

from lambdaweb.backend import LanguageBackend, RealLambdaBackend
from lambdaweb.model import SourceModel


def create_app(backend: LanguageBackend | None = None, model: SourceModel | None = None) -> Flask:
    app = Flask(__name__)
    app.config["BACKEND"] = backend if backend is not None else RealLambdaBackend()
    app.config["MODEL"] = model if model is not None else SourceModel()

    from lambdaweb.routes import bp

    app.register_blueprint(bp)
    return app
