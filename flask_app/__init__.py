from flask import Flask, jsonify
from werkzeug.exceptions import RequestEntityTooLarge
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

    upload_subdir = app.config.get('PRODUCT_UPLOAD_SUBDIR', 'uploads/products')
    upload_dir = os.path.join(app.static_folder, *upload_subdir.split('/'))
    os.makedirs(upload_dir, exist_ok=True)

    with app.app_context():
        from . import models  
        db.create_all()

        from .models import Product
        from .product_store import DEFAULT_PRODUCTS

        if Product.query.count() == 0:
            for product in DEFAULT_PRODUCTS:
                db.session.add(Product(
                    name=product['name'],
                    category=product['category'],
                    mrp=float(product['mrp']),
                    discount_price=float(product['discountPrice']),
                    description=product.get('desc', ''),
                    icon=product.get('icon', '📦'),
                    active=bool(product.get('active', True)),
                ))
            db.session.commit()

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
        from .routes.public import public_bp

        @app.errorhandler(RequestEntityTooLarge)
        def handle_request_too_large(error):
            return jsonify(error='One or more images are too large. Please upload smaller files or fewer images.'), 413

        app.register_blueprint(auth_bp)
        app.register_blueprint(admin_bp, url_prefix='/admin')
        app.register_blueprint(customer_bp, url_prefix='/shop')
        app.register_blueprint(public_bp)

    return app