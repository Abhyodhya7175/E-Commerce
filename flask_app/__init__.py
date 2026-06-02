from flask import Flask, jsonify
from werkzeug.exceptions import RequestEntityTooLarge
from .config import Config
from .extensions import db,mail
from .shop_state import get_commerce_state, get_csrf_token
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


def _ensure_product_schema():
    inspector = db.inspect(db.engine)
    if 'product' not in inspector.get_table_names():
        return

    columns = {column['name'] for column in inspector.get_columns('product')}

    missing_columns = {
        'brand': 'VARCHAR(100) NULL',
        'sku': 'VARCHAR(50) NULL UNIQUE',
        'slug': 'VARCHAR(255) NULL UNIQUE',
        'gst_percentage': 'FLOAT DEFAULT 18.0',
        'gst_type': "VARCHAR(20) DEFAULT 'inclusive'",
        'short_description': 'VARCHAR(500) NULL',
        'long_description': 'LONGTEXT NULL',
        'highlights': 'LONGTEXT NULL',
        'specifications': 'LONGTEXT NULL',
        'stock_quantity': 'INTEGER DEFAULT 0',
        'min_stock_alert': 'INTEGER DEFAULT 5',
        'cost_price': 'FLOAT NULL',
        'selling_price': 'FLOAT NULL',
        'product_weight': 'FLOAT NULL',
        'product_length': 'FLOAT NULL',
        'product_width': 'FLOAT NULL',
        'product_height': 'FLOAT NULL',
        'shipping_charges': 'FLOAT DEFAULT 0.0',
        'free_shipping': 'BOOLEAN DEFAULT FALSE',
        'product_status': 'VARCHAR(50) DEFAULT "Draft"',
        'featured_product': 'BOOLEAN DEFAULT FALSE',
        'trending_product': 'BOOLEAN DEFAULT FALSE',
        'best_seller': 'BOOLEAN DEFAULT FALSE',
        'new_arrival': 'BOOLEAN DEFAULT FALSE',
        'meta_title': 'VARCHAR(200) NULL',
        'meta_description': 'VARCHAR(500) NULL',
        'meta_keywords': 'LONGTEXT NULL',
        'canonical_url': 'VARCHAR(500) NULL',
        'og_image': 'VARCHAR(255) NULL',
        'updated_at': 'DATETIME NULL',
    }

    for column, definition in missing_columns.items():
        if column not in columns:
            db.session.execute(text(f'ALTER TABLE product ADD COLUMN {column} {definition}'))

    db.session.commit()


def _ensure_pincode_cache_schema():
    inspector = db.inspect(db.engine)
    if 'pincode_serviceability_cache' not in inspector.get_table_names():
        return

    columns = {column['name'] for column in inspector.get_columns('pincode_serviceability_cache')}
    missing_columns = {
        'pickup_pincode': 'VARCHAR(6) NULL',
        'weight': 'FLOAT NULL',
        'serviceable': 'BOOLEAN DEFAULT FALSE',
        'cod': 'BOOLEAN DEFAULT FALSE',
        'eta': 'VARCHAR(50) NULL',
        'courier_name': 'VARCHAR(120) NULL',
        'checked_at': 'DATETIME NULL',
    }

    for column, definition in missing_columns.items():
        if column not in columns:
            db.session.execute(text(f'ALTER TABLE pincode_serviceability_cache ADD COLUMN {column} {definition}'))

    db.session.commit()


def _ensure_user_schema():
    inspector = db.inspect(db.engine)
    if 'user' not in inspector.get_table_names():
        return

    columns = {column['name'] for column in inspector.get_columns('user')}
    missing_columns = {
        'is_verified': 'BOOLEAN DEFAULT 0',
        'last_login': 'DATETIME NULL',
    }
    for column, definition in missing_columns.items():
        if column not in columns:
            db.session.execute(text(f'ALTER TABLE user ADD COLUMN {column} {definition}'))

    db.session.commit()


def _ensure_coupon_schema():
    inspector = db.inspect(db.engine)
    if 'coupons' not in inspector.get_table_names():
        return

    columns = {column['name'] for column in inspector.get_columns('coupons')}
    missing_columns = {
        'name': 'VARCHAR(120) NULL',
        'kind': "VARCHAR(20) DEFAULT 'coupon'",
        'buy_x': 'INTEGER NULL',
        'buy_y': 'INTEGER NULL',
        'per_customer_limit': 'INTEGER NULL',
        'first_purchase_only': 'BOOLEAN DEFAULT 0',
        'new_customer_only': 'BOOLEAN DEFAULT 0',
        'is_draft': 'BOOLEAN DEFAULT 0',
        'starts_at': 'DATETIME NULL',
        'rules_json': 'TEXT NULL',
        'product_ids_json': 'TEXT NULL',
        'category_ids_json': 'TEXT NULL',
        'brand_ids_json': 'TEXT NULL',
        'exclude_product_ids_json': 'TEXT NULL',
        'exclude_category_ids_json': 'TEXT NULL',
        'flash_sale_json': 'TEXT NULL',
        'parent_id': 'INTEGER NULL',
        'updated_at': 'DATETIME NULL',
    }
    for column, definition in missing_columns.items():
        if column not in columns:
            db.session.execute(text(f'ALTER TABLE coupons ADD COLUMN {column} {definition}'))

    db.session.commit()


def _ensure_product_image_rows():
    from .models import Product, ProductImage

    changed = False
    for product in Product.query.all():
        if not product.image_url:
            continue

        existing = {
            image.image_url
            for image in ProductImage.query.filter_by(product_id=product.id).all()
        }
        if product.image_url in existing:
            continue

        max_order = db.session.query(db.func.max(ProductImage.order_index)).filter_by(product_id=product.id).scalar()
        db.session.add(ProductImage(
            product_id=product.id,
            image_url=product.image_url,
            order_index=(max_order or 0) + 1,
        ))
        changed = True

    if changed:
        db.session.commit()


def _deduplicate_products():
    from .models import Product, ProductImage, Review, _slugify

    products_by_key = {}
    for product in Product.query.order_by(Product.id.asc()).all():
        key = _slugify(product.name)
        products_by_key.setdefault(key, []).append(product)

    changed = False

    def product_score(product):
        return (
            (8 if product.sku else 0)
            + (6 if product.brand else 0)
            + (5 if product.stock_quantity and product.stock_quantity > 0 else 0)
            + (4 if product.product_status == 'Published' else 0)
            + (3 if product.short_description or product.long_description else 0)
            + (2 * len(product.images))
            + (1 if product.image_url else 0)
            + (product.id or 0) / 100000
        )

    for duplicates in products_by_key.values():
        if len(duplicates) < 2:
            continue

        keeper = max(duplicates, key=product_score)
        existing_urls = {image.image_url for image in keeper.images}
        max_order = db.session.query(db.func.max(ProductImage.order_index)).filter_by(product_id=keeper.id).scalar() or 0

        for duplicate in duplicates:
            if duplicate.id == keeper.id:
                continue

            for field in (
                'brand', 'sku', 'description', 'short_description', 'long_description',
                'highlights', 'specifications', 'meta_title', 'meta_description',
                'meta_keywords', 'canonical_url', 'og_image',
            ):
                if not getattr(keeper, field, None) and getattr(duplicate, field, None):
                    setattr(keeper, field, getattr(duplicate, field))

            for field in ('mrp', 'discount_price', 'selling_price', 'cost_price', 'gst_percentage', 'shipping_charges'):
                if not getattr(keeper, field, None) and getattr(duplicate, field, None):
                    setattr(keeper, field, getattr(duplicate, field))

            if not keeper.stock_quantity and duplicate.stock_quantity:
                keeper.stock_quantity = duplicate.stock_quantity
            if not keeper.image_url and duplicate.image_url:
                keeper.image_url = duplicate.image_url

            duplicate_urls = [image.image_url for image in duplicate.images]
            if duplicate.image_url:
                duplicate_urls.insert(0, duplicate.image_url)

            for image_url in duplicate_urls:
                if not image_url or image_url in existing_urls:
                    continue
                max_order += 1
                db.session.add(ProductImage(
                    product_id=keeper.id,
                    image_url=image_url,
                    order_index=max_order,
                ))
                existing_urls.add(image_url)

            Review.query.filter_by(product_id=duplicate.id).update({'product_id': keeper.id})
            db.session.delete(duplicate)
            changed = True

        db.session.flush()
        primary_image = ProductImage.query.filter_by(product_id=keeper.id).order_by(ProductImage.order_index.asc()).first()
        keeper.image_url = primary_image.image_url if primary_image else None

    if changed:
        db.session.commit()


def _ensure_demo_users():
    from .models import User

    defaults = [
        ("customer@demo.com", "Alex Johnson", "customer", "customer123"),
        ("admin@demo.com", "Sara Admin", "admin", "admin123"),
    ]

    changed = False
    for email, name, role, password in defaults:
        user = User.query.filter_by(email=email).first()
        if user:
            continue

        user = User(name=name, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        changed = True

    if changed:
        db.session.commit()


def create_app():
    # Explicitly configure static and template folders
    static_folder = os.path.join(os.path.dirname(__file__), 'static')
    template_folder = os.path.join(os.path.dirname(__file__), 'templates')
    app = Flask(__name__, static_folder=static_folder, static_url_path='/static', template_folder=template_folder)
    app.config.from_object(Config)
    db.init_app(app)
    mail.init_app(app)

    if app.config.get("MAIL_SUPPRESS_SEND"):
        app.logger.warning(
            "Email OTP is OFF — set MAIL_USERNAME and MAIL_PASSWORD in flask_app/.env, then restart."
        )
    else:
        app.logger.info(
            "Email OTP is ON (SMTP %s:%s as %s)",
            app.config.get("MAIL_SERVER"),
            app.config.get("MAIL_PORT"),
            app.config.get("MAIL_USERNAME"),
        )

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
        _ensure_product_schema()
        _ensure_pincode_cache_schema()
        _ensure_user_schema()
        _ensure_coupon_schema()

        from .models import Product, ProductCategory, ProductBrand
        from .product_store import DEFAULT_PRODUCTS

        # Seed default categories
        DEFAULT_CATEGORIES = [
            {'name': 'Electronics', 'description': 'Gadgets, devices, and tech accessories'},
            {'name': 'Fashion', 'description': 'Clothing, shoes, and fashion accessories'},
            {'name': 'Sports', 'description': 'Sports equipment and athletic wear'},
            {'name': 'Home', 'description': 'Home decor, kitchenware, and furniture'},
            {'name': 'Books', 'description': 'Books, ebooks, and educational materials'},
        ]
        for cat_data in DEFAULT_CATEGORIES:
            if not ProductCategory.query.filter_by(name=cat_data['name']).first():
                from .models import _slugify
                category = ProductCategory(
                    name=cat_data['name'],
                    slug=_slugify(cat_data['name']),
                    description=cat_data['description']
                )
                db.session.add(category)
        db.session.commit()

        # Seed default brands
        DEFAULT_BRANDS = [
            {'name': 'UrbanCart', 'logo_url': None},
            {'name': 'TechPro', 'logo_url': None},
            {'name': 'StyleX', 'logo_url': None},
            {'name': 'FitZone', 'logo_url': None},
            {'name': 'HomePlus', 'logo_url': None},
            {'name': 'Premium', 'logo_url': None},
            {'name': 'Elite', 'logo_url': None},
            {'name': 'Classic', 'logo_url': None},
        ]
        for brand_data in DEFAULT_BRANDS:
            if not ProductBrand.query.filter_by(name=brand_data['name']).first():
                from .models import _slugify
                brand = ProductBrand(
                    name=brand_data['name'],
                    slug=_slugify(brand_data['name']),
                    logo_url=brand_data['logo_url']
                )
                db.session.add(brand)
        db.session.commit()

        if Product.query.count() == 0:
            from .models import _slugify

            existing_slugs = {slug for (slug,) in db.session.query(Product.slug).all() if slug}
            for product in DEFAULT_PRODUCTS:
                base_slug = _slugify(product['name'])
                slug = base_slug
                suffix = 2
                while slug in existing_slugs:
                    slug = f"{base_slug}-{suffix}"
                    suffix += 1
                existing_slugs.add(slug)

                db.session.add(Product(
                    name=product['name'],
                    category=product['category'],
                    slug=slug,
                    mrp=float(product['mrp']),
                    discount_price=float(product['discountPrice']),
                    description=product.get('desc', ''),
                    icon=product.get('icon', '📦'),
                    active=bool(product.get('active', True)),
                ))
            db.session.commit()

        _ensure_product_image_rows()
        _deduplicate_products()
        _ensure_demo_users()

        from .services.checkout_service import seed_default_coupons

        seed_default_coupons()

        from .extensions import login_manager
        # initialize login manager
        login_manager.init_app(app)
        app.jinja_env.globals['csrf_token'] = get_csrf_token

        @app.context_processor
        def inject_commerce_state():
            state = get_commerce_state()
            return {
                'cart_count': state['cart_count'],
                'wishlist_count': state['wishlist_count'],
                'wishlist_ids': state['wishlist_ids'],
                'cart_quantities': state['cart_quantities'],
            }

        @login_manager.user_loader
        def load_user(user_id):
            from .models import User

            return User.query.get(int(user_id))

        from .routes.auth import auth_bp
        from .routes.admin import admin_bp
        from .routes.customer import customer_bp
        from .routes.commerce import commerce_bp
        from .routes.checkout import checkout_bp
        from .routes.public import public_bp
        from .routes.blog import blog_bp

        @app.errorhandler(RequestEntityTooLarge)
        def handle_request_too_large(error):
            return jsonify(error='One or more images are too large. Please upload smaller files or fewer images.'), 413

        app.register_blueprint(auth_bp)
        app.register_blueprint(admin_bp, url_prefix='/admin')
        app.register_blueprint(customer_bp, url_prefix='/shop')
        app.register_blueprint(checkout_bp, url_prefix='/shop')
        app.register_blueprint(commerce_bp)
        app.register_blueprint(public_bp)
        app.register_blueprint(blog_bp)

    return app
