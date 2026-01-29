from flask import Flask
from .config import Config
from .db import db, migrate


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    with app.app_context():
        # IMPORTANT: load models so tables are registered with SQLAlchemy
        from . import models  # noqa: F401

        db.create_all()
        app.logger.warning("✅ db.create_all() executed")

    # Optional, fine to keep even if you aren't using migrations
    migrate.init_app(app, db)

    from .routes import bp as main_bp
    app.register_blueprint(main_bp)

    return app
