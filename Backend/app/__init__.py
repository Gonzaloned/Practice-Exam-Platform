from flask import Flask
from flask_cors import CORS
from .config import Config
from .extensions import db, bcrypt, jwt

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app, resources={r"/api/*": {"origins": "*"}})

    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)

    from .routes.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix="/api/auth")

    from .routes.health import health_bp
    app.register_blueprint(health_bp, url_prefix="/api")

    with app.app_context():
        from . import models
        db.create_all()

    return app
