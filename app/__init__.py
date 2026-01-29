from flask import Flask
from .config import Config
from .db import db, migrate


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    # Create tables automatically if they don't exist yet (no migrations required)
    with app.app_context():
        db.create_all()

    # Keep migrate init if you might use migrations later; harmless to leave in.
    migrate.init_app(app, db)

    from .routes import bp as main_bp
    app.register_blueprint(main_bp)

    return app
