from flask import Flask
from .config import Config
from .db import db, migrate


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    with app.app_context():
    db.create_all()
    migrate.init_app(app, db)

    from .routes import bp as main_bp
    app.register_blueprint(main_bp)

    return app
