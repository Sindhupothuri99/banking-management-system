from flask import Flask
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

from app.models import db, User
from config import Config

login_manager = LoginManager()
csrf = CSRFProtect()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Database configuration
    db.init_app(app)

    # Enable CSRF protection
    csrf.init_app(app)

    # Login configuration
    login_manager.init_app(app)
    login_manager.login_view = "main.login"

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from app.routes import main
    app.register_blueprint(main)

    with app.app_context():
        db.create_all()

    return app