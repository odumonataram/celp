"""
app/__init__.py

Application factory. Using create_app() instead of a bare module-level Flask
app means we can spin up multiple configured instances (handy for tests) and
keeps import order sane -- extensions are created in app/extensions.py and
only *attached* here, which is what avoids circular imports between
app/models.py and the blueprint packages.
"""

from flask import Flask
from config import config_by_name
from app.extensions import db, login_manager, csrf, migrate


def create_app(config_name="development"):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_by_name[config_name])

    # Extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)

    # Blueprints -- each module is self-contained (routes + its own forms
    # where relevant) so features can be developed/reviewed independently.
    from app.auth.routes import auth_bp
    from app.main.routes import main_bp
    from app.translator.routes import translator_bp
    from app.dictionary.routes import dictionary_bp
    from app.quiz.routes import quiz_bp
    from app.dashboard.routes import dashboard_bp
    from app.admin.routes import admin_bp
    from app.lecturer.routes import lecturer_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(translator_bp, url_prefix="/translate")
    app.register_blueprint(dictionary_bp, url_prefix="/dictionary")
    app.register_blueprint(quiz_bp, url_prefix="/quiz")
    app.register_blueprint(dashboard_bp, url_prefix="/dashboard")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(lecturer_bp, url_prefix="/lecturer")

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Make "now" and the supported language list available in every template
    # without passing them through each render_template() call individually.
    @app.context_processor
    def inject_globals():
        from datetime import datetime
        return {
            "current_year": datetime.utcnow().year,
            "supported_languages": app.config["SUPPORTED_LANGUAGES"],
        }

    register_cli_commands(app)
    register_error_handlers(app)

    return app


def register_cli_commands(app):
    """`flask seed-db` populates languages + sample vocabulary so the app is
    demoable immediately after `flask db upgrade` on a fresh database."""

    @app.cli.command("seed-db")
    def seed_db():
        from app.seed import run_seed
        run_seed()
        print("Database seeded.")


def register_error_handlers(app):
    from flask import render_template

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(500)
    def server_error(e):
        return render_template("errors/500.html"), 500
