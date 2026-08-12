"""
app/extensions.py

Flask extensions are instantiated here, unbound, and attached to the app
inside the application factory (app/__init__.py) via init_app(). This
pattern avoids circular imports: blueprints can import `db` or `login_manager`
from this module without ever importing the app package itself.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf import CSRFProtect
from flask_migrate import Migrate

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
migrate = Migrate()

login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "info"
