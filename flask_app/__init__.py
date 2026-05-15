from flask import Flask, jsonify
from werkzeug.exceptions import RequestEntityTooLarge
from .config import Config
from .extensions import db
from sqlalchemy import text
import os


def _ensure_offer_banner_schema():
    inspector = db.inspect(db.engine)
    if 'offer_banners' not in inspector.get_table_names():
        return

    columns = {column['name'] for column in inspector.get_columns('offer_banners')}
    dialect = db.engine.dialect.name

    if 'buttonn_text' in columns and 'button_text' not in columns:
        if dialect == 'mysql':
            db.session.execute(text('ALTER TABLE offer_banners CHANGE buttonn_text button_text VARCHAR(100) NULL'))
        else:
            db.session.execute(text('ALTER TABLE offer_banners ADD COLUMN button_text VARCHAR(100) NULL'))
            db.session.execute(text('UPDATE offer_banners SET button_text = buttonn_text WHERE button_text IS NULL'))
        columns.add('button_text')

    missing_columns = {
        'button_text': 'VARCHAR(100) NULL',
        'button_link': 'VARCHAR(300) NULL',
        'background_color': "VARCHAR(20) NULL DEFAULT '#f5f5f5'",
        'is_active': 'BOOLEAN DEFAULT TRUE',
        'display_order': 'INTEGER DEFAULT 0',
        'start_date': 'DATETIME NULL',
        'end_date': 'DATETIME NULL',
        'created_at': 'DATETIME NULL',
    }
    for column, definition in missing_columns.items():
        if column not in columns:
            db.session.execute(text(f'ALTER TABLE offer_banners ADD COLUMN {column} {definition}'))

    db.session.commit()


def create_app():
    # Explicitly configure static and template folders
    static_folder = os.path.join(os.path.dirname(__file__), 'static')
    template_folder = os.path.join(os.path.dirname(__file__), 'templates')
    app = Flask(__name__, static_folder=static_folder, static_url_path='/static', template_folder=template_folder)
    app.config.from_object(Config)
    db.init_app(app)

    for upload_subdir in (
        app.config.get('PRODUCT_UPLOAD_SUBDIR', 'uploads/products'),
        app.config.get('OFFER_BANNER_UPLOAD_SUBDIR', 'uploads/banners'),
    ):
        upload_dir = os.path.join(app.static_folder, *upload_subdir.split('/'))
        os.makedirs(upload_dir, exist_ok=True)

    with app.app_context():
        from . import models  
        db.create_all()
        _ensure_offer_banner_schema()

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
        from .routes.blog import blog_bp

        @app.errorhandler(RequestEntityTooLarge)
        def handle_request_too_large(error):
            return jsonify(error='One or more images are too large. Please upload smaller files or fewer images.'), 413

        app.register_blueprint(auth_bp)
        app.register_blueprint(admin_bp, url_prefix='/admin')
        app.register_blueprint(customer_bp, url_prefix='/shop')
        app.register_blueprint(public_bp)
        app.register_blueprint(blog_bp)

    return app
