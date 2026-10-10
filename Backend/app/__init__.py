from flask import Flask
from flask_cors import CORS
from .config import Config
from .extensions import db, bcrypt, jwt, socketio

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

    from .routes.attempt_create import attempt_create_bp
    app.register_blueprint(attempt_create_bp, url_prefix="/api")

    from .routes.set_attempt_data import set_attempt_data_bp
    app.register_blueprint(set_attempt_data_bp, url_prefix="/api")

    from .routes.vm_environment_create import vm_environment_create_bp
    app.register_blueprint(vm_environment_create_bp, url_prefix="/api")

    from .routes import ssh_attempt_connection, ssh_console_flow

    socketio.init_app(
        app,
        cors_allowed_origins=app.config["SOCKETIO_CORS_ALLOWED_ORIGINS"],
    )

    with app.app_context():
        from . import models
        db.create_all()

    return app
