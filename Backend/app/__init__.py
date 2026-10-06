from flask import Flask
from flask_cors import CORS
from .config import Config
from .extensions import db, bcrypt, jwt

def create_app(test_config: dict | None = None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config is not None:
        app.config.update(test_config)

    CORS(app, resources={r"/api/*": {"origins": "*"}})

    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)

    from .routes.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix="/api/auth")

    from .routes.health import health_bp
    app.register_blueprint(health_bp, url_prefix="/api")

    from .routes.exam_sessions import exam_sessions_bp
    app.register_blueprint(exam_sessions_bp, url_prefix="/api/exam")

    with app.app_context():
        from . import models
        db.create_all()

    return app
