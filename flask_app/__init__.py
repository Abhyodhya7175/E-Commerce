from flask import Flask
from .config import Config
from .extensions import db
import os

def create_app():
    # Explicitly configure static and template folders
    static_folder = os.path.join(os.path.dirname(__file__), 'static')
    template_folder = os.path.join(os.path.dirname(__file__), 'templates')
    app = Flask(__name__, static_folder=static_folder, static_url_path='/static', template_folder=template_folder)
    app.config.from_object(Config)
    db.init_app(app)

    with app.app_context():
        from . import models  
        db.create_all()

        from .extensions import login_manager
        # initialize login manager
        login_manager.init_app(app)

        @login_manager.user_loader
        def load_user(user_id):
            from .models import User

            return User.query.get(int(user_id))

        from .routes.auth import auth_bp
        from .routes.admin import admin_bp
        from .routes.customer import customer_bp

        app.register_blueprint(auth_bp)
        app.register_blueprint(admin_bp, url_prefix='/admin')
        app.register_blueprint(customer_bp, url_prefix='/shop')

    return app