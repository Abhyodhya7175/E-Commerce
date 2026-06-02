from .extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import json
import re
from datetime import datetime


def _slugify(value: str) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "product"


def _split_admin_list(value):
    value = str(value or '').strip()
    if not value:
        return []

    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        parsed = None

    if isinstance(parsed, list):
        return [str(item).strip() for item in parsed if str(item).strip()]
    if isinstance(parsed, dict):
        return [f"{key}: {val}" for key, val in parsed.items() if str(val).strip()]

    parts = re.split(r'[\n,;]+', value)
    return [part.strip(' -\t') for part in parts if part.strip(' -\t')]


def _parse_specifications(value):
    value = str(value or '').strip()
    if not value:
        return []

    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        parsed = None

    if isinstance(parsed, dict):
        return [
            {'label': str(key).strip(), 'value': str(val).strip()}
            for key, val in parsed.items()
            if str(key).strip() and str(val).strip()
        ]
    if isinstance(parsed, list):
        return [
            {'label': 'Detail', 'value': str(item).strip()}
            for item in parsed
            if str(item).strip()
        ]

    segments = re.split(r'[\n;]+', value)
    if len([segment for segment in segments if segment.strip()]) == 1 and value.count(':') > 1:
        segments = re.split(r',+', value)

    specs = []
    for line in segments:
        line = line.strip(' -\t')
        if not line:
            continue
        if ':' in line:
            label, val = line.split(':', 1)
        elif '=' in line:
            label, val = line.split('=', 1)
        else:
            label, val = 'Detail', line
        label = label.strip()
        val = val.strip()
        if label and val:
            specs.append({'label': label, 'value': val})
    return specs


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)
    role = db.Column(db.String(20), nullable=False, default='customer')
    is_verified=db.Column(db.Boolean, default=False)
    last_login=db.Column(db.DateTime, nullable=True)
    created_at=db.Column(db.DateTime, default=datetime.utcnow)


    def set_password(self, password):
        if not password:
            self.password_hash = None
            return
        self.password_hash = generate_password_hash(password)

    @property
    def has_password(self):
        return bool(self.password_hash)

    def check_password(self, password):
        if not self.password_hash or not password:
            return False
        return check_password_hash(self.password_hash, password)
    


class EmailOTP(db.Model):
    __tablename__ = 'email_otps'
    id=db.Column(db.Integer, primary_key=True)
    email=db.Column(db.String(100), nullable=False)
    otp=db.Column(db.String(255), nullable=False)
    expires_at=db.Column(db.DateTime, nullable=False)
    is_used=db.Column(db.Boolean, default=False)
    created_at=db.Column(db.DateTime, default=datetime.utcnow)



class ProductCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {'id': self.id, 'name': self.name, 'slug': self.slug, 'description': self.description}


class ProductBrand(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    logo_url = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {'id': self.id, 'name': self.name, 'slug': self.slug, 'logo_url': self.logo_url}


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(80), nullable=False)
    brand = db.Column(db.String(100), nullable=True)
    sku = db.Column(db.String(50), unique=True, nullable=True)
    slug = db.Column(db.String(255), unique=True, nullable=False)
    mrp = db.Column(db.Float, nullable=False)
    discount_price = db.Column(db.Float, nullable=False)
    selling_price = db.Column(db.Float, nullable=True)
    cost_price = db.Column(db.Float, nullable=True)
    gst_percentage = db.Column(db.Float, default=18.0, nullable=False)
    gst_type = db.Column(db.String(20), default='inclusive', nullable=False)
    description = db.Column(db.Text, nullable=True)
    short_description = db.Column(db.String(500), nullable=True)
    long_description = db.Column(db.Text, nullable=True)
    highlights = db.Column(db.Text, nullable=True)
    specifications = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(20), nullable=False, default='📦')
    image_url = db.Column(db.String(255), nullable=True)
    stock_quantity = db.Column(db.Integer, default=0, nullable=False)
    min_stock_alert = db.Column(db.Integer, default=5, nullable=False)
    product_weight = db.Column(db.Float, nullable=True)
    product_length = db.Column(db.Float, nullable=True)
    product_width = db.Column(db.Float, nullable=True)
    product_height = db.Column(db.Float, nullable=True)
    shipping_charges = db.Column(db.Float, default=0.0, nullable=False)
    free_shipping = db.Column(db.Boolean, default=False, nullable=False)
    product_status = db.Column(db.String(50), default='Draft', nullable=False)
    featured_product = db.Column(db.Boolean, default=False, nullable=False)
    trending_product = db.Column(db.Boolean, default=False, nullable=False)
    best_seller = db.Column(db.Boolean, default=False, nullable=False)
    new_arrival = db.Column(db.Boolean, default=False, nullable=False)
    meta_title = db.Column(db.String(200), nullable=True)
    meta_description = db.Column(db.String(500), nullable=True)
    meta_keywords = db.Column(db.Text, nullable=True)
    canonical_url = db.Column(db.String(500), nullable=True)
    og_image = db.Column(db.String(255), nullable=True)
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    reviews = db.relationship(
        "Review",
        backref="product",
        lazy=True,
        cascade="all, delete-orphan")

    images = db.relationship(
    "ProductImage",
    backref="product",
    lazy=True,
    order_by="ProductImage.order_index",
    cascade="all, delete-orphan")

    @property
    def stock_status(self):
        if self.product_status == 'Out of Stock':
            return 'Out of Stock'
        if self.stock_quantity <= 0:
            return 'Out of Stock'
        elif self.stock_quantity <= self.min_stock_alert:
            return 'Low Stock'
        return 'In Stock'

    @property
    def average_rating(self):
        """Calculate average rating from all reviews for this product"""
        if not self.reviews:
            return 0
        total = sum(review.rating for review in self.reviews)
        return round(total / len(self.reviews), 1)

    @property
    def review_count(self):
        """Get total number of reviews for this product"""
        return len(self.reviews)

    def to_dict(self):
        mrp = float(self.mrp or 0)
        discount_price = float(self.discount_price or 0)
        discount_percent = 0
        if mrp > 0 and 0 <= discount_price <= mrp:
            discount_percent = round(((mrp - discount_price) / mrp) * 100)

        image_urls = [img.image_url for img in sorted(self.images, key=lambda img: (img.order_index or 0, img.id or 0))]

        profit_margin = 0
        cost = float(self.cost_price or 0)
        selling = float(self.selling_price or discount_price)
        if cost > 0:
            profit_margin = round(((selling - cost) / cost) * 100, 2)

        gst_pct = float(self.gst_percentage or 0)
        gst_type = self.gst_type or 'inclusive'

        if gst_type == 'inclusive':
            base_price = selling / (1 + gst_pct / 100) if gst_pct > 0 else selling
            gst_amount = selling - base_price
            final_price = selling
        else:
            base_price = selling
            gst_amount = round((selling * (gst_pct / 100)), 2)
            final_price = selling + gst_amount

        gst_amount = round(gst_amount, 2)
        base_price = round(base_price, 2)
        final_price = round(final_price, 2)
        parsed_highlights = _split_admin_list(self.highlights)
        parsed_specs = _parse_specifications(self.specifications)

        return {
            'id': self.id,
            'slug': self.slug or _slugify(self.name),
            'name': self.name,
            'category': self.category,
            'brand': self.brand or '',
            'sku': self.sku or f"UC-{(self.id or 0):05d}",
            'mrp': mrp,
            'discountPrice': discount_price,
            'sellingPrice': float(self.selling_price or discount_price),
            'costPrice': cost,
            'discountPercent': discount_percent,
            'gstPercentage': float(self.gst_percentage or 0),
            'gstType': gst_type,
            'basePrice': base_price,
            'gstAmount': gst_amount,
            'finalPrice': final_price,
            'profitMargin': profit_margin,
            'stockQuantity': self.stock_quantity,
            'minStockAlert': self.min_stock_alert,
            'stockStatus': self.stock_status,
            'weight': self.product_weight,
            'length': self.product_length,
            'width': self.product_width,
            'height': self.product_height,
            'shippingCharges': float(self.shipping_charges or 0),
            'freeShipping': self.free_shipping,
            'productStatus': self.product_status,
            'shortDesc': self.short_description or '',
            'longDesc': self.long_description or (self.description or ''),
            'desc': self.description or '',
            'highlights': self.highlights or '',
            'highlightItems': parsed_highlights,
            'specifications': self.specifications or '',
            'specificationItems': parsed_specs,
            'icon': self.icon,
            'rating': self.average_rating,
            'reviewCount': self.review_count,
            'imageUrls': image_urls,
            'imageUrl': image_urls[0] if len(image_urls) else None,
            'active': self.active,
            'featured': self.featured_product,
            'trending': self.trending_product,
            'bestSeller': self.best_seller,
            'newArrival': self.new_arrival,
            'metaTitle': self.meta_title or '',
            'metaDescription': self.meta_description or '',
            'metaKeywords': self.meta_keywords or '',
            'canonicalUrl': self.canonical_url or '',
            'ogImage': self.og_image or '',
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None,
        }


class ProductImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id', ondelete='CASCADE'), nullable=False)
    image_url = db.Column(db.String(255), nullable=False)
    order_index = db.Column(db.Integer, nullable=False, default=0)

class Review(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    product_id=db.Column(db.Integer,db.ForeignKey('product.id'),nullable=False)
    name=db.Column(db.String(100),nullable=False)
    message=db.Column(db.Text,nullable=False)
    rating=db.Column(db.Integer,nullable=False)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)


class SearchHistory(db.Model):
    """Track user search queries for suggestions and analytics"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=True)  # NULL for guest searches
    query = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(80), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)  # IPv4 or IPv6
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'query': self.query,
            'category': self.category,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class PincodeServiceabilityCache(db.Model):
    __tablename__ = 'pincode_serviceability_cache'

    id = db.Column(db.Integer, primary_key=True)
    pincode = db.Column(db.String(6), nullable=False, index=True)
    pickup_pincode = db.Column(db.String(6), nullable=True)
    weight = db.Column(db.Float, nullable=True)
    serviceable = db.Column(db.Boolean, nullable=False, default=False)
    cod = db.Column(db.Boolean, nullable=False, default=False)
    eta = db.Column(db.String(50), nullable=True)
    courier_name = db.Column(db.String(120), nullable=True)
    checked_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class CartItem(db.Model):
    __tablename__ = 'cart_items'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id', ondelete='CASCADE'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = db.relationship('User', backref=db.backref('cart_items', lazy=True, cascade='all, delete-orphan'))
    product = db.relationship('Product')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'product_id', name='uq_cart_item_user_product'),
    )


class WishlistItem(db.Model):
    __tablename__ = 'wishlist_items'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship('User', backref=db.backref('wishlist_items', lazy=True, cascade='all, delete-orphan'))
    product = db.relationship('Product')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'product_id', name='uq_wishlist_item_user_product'),
    )


class Blog(db.Model):
    """Blog posts for content marketing"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False)
    content = db.Column(db.Text, nullable=False)
    excerpt = db.Column(db.String(500), nullable=True)
    featured_image = db.Column(db.String(255), nullable=True)
    category = db.Column(db.String(100), nullable=False, default='General')
    author = db.Column(db.String(100), nullable=False, default='UrbanCart Team')
    views = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published = db.Column(db.Boolean, default=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'slug': self.slug,
            'excerpt': self.excerpt or self.content[:200] + '...',
            'featured_image': self.featured_image or '📰',
            'category': self.category,
            'author': self.author,
            'views': self.views,
            'created_at': self.created_at.strftime('%Y-%m-%d') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d') if self.updated_at else None,
        }



class OfferBanner(db.Model):
    __tablename__ = 'offer_banners'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    subtitle = db.Column(db.String(500), nullable=True)
    image = db.Column(db.String(300), nullable=False)
    button_text = db.Column(db.String(100), nullable=True)
    button_link = db.Column(db.String(300), nullable=True)
    background_color = db.Column(db.String(20), nullable=True, default="#f5f5f5")
    is_active = db.Column(db.Boolean, default=True)
    display_order = db.Column(db.Integer, default=0)
    start_date = db.Column(db.DateTime, nullable=True)
    end_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def is_visible(self, now=None):
        now = now or datetime.utcnow()
        if not self.is_active:
            return False
        if self.start_date and self.start_date > now:
            return False
        if self.end_date and self.end_date < now:
            return False
        return True

    def schedule_status(self, now=None):
        now = now or datetime.utcnow()
        if not self.is_active:
            return 'inactive'
        if self.start_date and self.start_date > now:
            return 'scheduled'
        if self.end_date and self.end_date < now:
            return 'expired'
        return 'live'

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'subtitle': self.subtitle or '',
            'image': self.image,
            'buttonText': self.button_text or '',
            'buttonLink': self.button_link or '',
            'backgroundColor': self.background_color or '#f5f5f5',
            'active': bool(self.is_active),
            'displayOrder': int(self.display_order or 0),
            'startDate': self.start_date.strftime('%Y-%m-%dT%H:%M') if self.start_date else '',
            'endDate': self.end_date.strftime('%Y-%m-%dT%H:%M') if self.end_date else '',
            'createdAt': self.created_at.isoformat() if self.created_at else '',
        }


class UserAddress(db.Model):
    __tablename__ = 'user_addresses'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    full_name = db.Column(db.String(120), nullable=False)
    mobile = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    house = db.Column(db.String(200), nullable=False)
    street = db.Column(db.String(255), nullable=False)
    landmark = db.Column(db.String(255), nullable=True)
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(100), nullable=False)
    pincode = db.Column(db.String(6), nullable=False)
    country = db.Column(db.String(80), nullable=False, default='India')
    is_default = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = db.relationship('User', backref=db.backref('addresses', lazy=True, cascade='all, delete-orphan'))

    def to_dict(self):
        return {
            'id': self.id,
            'fullName': self.full_name,
            'mobile': self.mobile,
            'email': self.email or '',
            'house': self.house,
            'street': self.street,
            'landmark': self.landmark or '',
            'city': self.city,
            'state': self.state,
            'pincode': self.pincode,
            'country': self.country,
            'isDefault': bool(self.is_default),
            'label': f'{self.house}, {self.city} — {self.pincode}',
        }


def _json_load(text, default=None):
    if default is None:
        default = []
    if not text:
        return default
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return default


def _json_dump(value):
    return json.dumps(value or [])


class Coupon(db.Model):
    __tablename__ = 'coupons'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=True)
    code = db.Column(db.String(40), unique=True, nullable=False, index=True)
    description = db.Column(db.String(255), nullable=True)
    kind = db.Column(db.String(20), nullable=False, default='coupon')  # coupon | promotion
    discount_type = db.Column(db.String(20), nullable=False, default='percent')
    discount_value = db.Column(db.Float, nullable=False, default=0.0)
    min_order_amount = db.Column(db.Float, default=0.0, nullable=False)
    max_discount = db.Column(db.Float, nullable=True)
    buy_x = db.Column(db.Integer, nullable=True)
    buy_y = db.Column(db.Integer, nullable=True)
    usage_limit = db.Column(db.Integer, nullable=True)
    per_customer_limit = db.Column(db.Integer, nullable=True)
    used_count = db.Column(db.Integer, default=0, nullable=False)
    first_purchase_only = db.Column(db.Boolean, default=False, nullable=False)
    new_customer_only = db.Column(db.Boolean, default=False, nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    is_draft = db.Column(db.Boolean, default=False, nullable=False)
    starts_at = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    rules_json = db.Column(db.Text, nullable=True)
    product_ids_json = db.Column(db.Text, nullable=True)
    category_ids_json = db.Column(db.Text, nullable=True)
    brand_ids_json = db.Column(db.Text, nullable=True)
    exclude_product_ids_json = db.Column(db.Text, nullable=True)
    exclude_category_ids_json = db.Column(db.Text, nullable=True)
    flash_sale_json = db.Column(db.Text, nullable=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('coupons.id'), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    children = db.relationship('Coupon', backref=db.backref('parent', remote_side=[id]), lazy='dynamic')

    def compute_status(self) -> str:
        now = datetime.utcnow()
        if self.is_draft:
            return 'draft'
        if self.starts_at and self.starts_at > now:
            return 'scheduled'
        if self.expires_at and self.expires_at < now:
            return 'expired'
        if not self.active:
            return 'expired'
        return 'active'

    def to_dict(self, admin: bool = False):
        base = {
            'code': self.code,
            'description': self.description or '',
            'discountType': self.discount_type,
            'discountValue': float(self.discount_value or 0),
            'minOrderAmount': float(self.min_order_amount or 0),
            'maxDiscount': float(self.max_discount) if self.max_discount is not None else None,
        }
        if not admin:
            return base
        return {
            **base,
            'id': self.id,
            'name': self.name or self.code,
            'kind': self.kind or 'coupon',
            'status': self.compute_status(),
            'buyX': self.buy_x,
            'buyY': self.buy_y,
            'usageLimit': self.usage_limit,
            'perCustomerLimit': self.per_customer_limit,
            'usedCount': int(self.used_count or 0),
            'firstPurchaseOnly': bool(self.first_purchase_only),
            'newCustomerOnly': bool(self.new_customer_only),
            'active': bool(self.active),
            'isDraft': bool(self.is_draft),
            'startsAt': self.starts_at.isoformat() if self.starts_at else None,
            'expiresAt': self.expires_at.isoformat() if self.expires_at else None,
            'rules': _json_load(self.rules_json, []),
            'productIds': _json_load(self.product_ids_json, []),
            'categoryIds': _json_load(self.category_ids_json, []),
            'brandIds': _json_load(self.brand_ids_json, []),
            'excludeProductIds': _json_load(self.exclude_product_ids_json, []),
            'excludeCategoryIds': _json_load(self.exclude_category_ids_json, []),
            'flashSale': _json_load(self.flash_sale_json, {}),
            'parentId': self.parent_id,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None,
        }


class LoyaltyReward(db.Model):
    __tablename__ = 'loyalty_rewards'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    coins_required = db.Column(db.Integer, nullable=False, default=0)
    reward_type = db.Column(db.String(30), nullable=False, default='coupon')
    reward_value = db.Column(db.Float, nullable=True)
    expiry_days = db.Column(db.Integer, nullable=True)
    coupon_id = db.Column(db.Integer, db.ForeignKey('coupons.id', ondelete='SET NULL'), nullable=True)
    config_json = db.Column(db.Text, nullable=True)
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    coupon = db.relationship('Coupon', backref=db.backref('loyalty_rewards', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'coinsRequired': int(self.coins_required or 0),
            'rewardType': self.reward_type,
            'rewardValue': float(self.reward_value) if self.reward_value is not None else None,
            'expiryDays': self.expiry_days,
            'couponId': self.coupon_id,
            'config': _json_load(self.config_json, {}),
            'active': bool(self.active),
            'createdAt': self.created_at.isoformat() if self.created_at else None,
        }


class LoyaltyWallet(db.Model):
    __tablename__ = 'loyalty_wallets'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), unique=True, nullable=False)
    balance_coins = db.Column(db.Integer, default=0, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = db.relationship('User', backref=db.backref('loyalty_wallet', uselist=False, cascade='all, delete-orphan'))


class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(32), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True, index=True)
    guest_token = db.Column(db.String(64), nullable=True, index=True)

    contact_name = db.Column(db.String(120), nullable=False)
    contact_email = db.Column(db.String(120), nullable=False)
    contact_phone = db.Column(db.String(20), nullable=False)

    shipping_full_name = db.Column(db.String(120), nullable=False)
    shipping_mobile = db.Column(db.String(20), nullable=False)
    shipping_house = db.Column(db.String(200), nullable=False)
    shipping_street = db.Column(db.String(255), nullable=False)
    shipping_landmark = db.Column(db.String(255), nullable=True)
    shipping_city = db.Column(db.String(100), nullable=False)
    shipping_state = db.Column(db.String(100), nullable=False)
    shipping_pincode = db.Column(db.String(6), nullable=False)
    shipping_country = db.Column(db.String(80), nullable=False, default='India')

    shipping_method = db.Column(db.String(30), nullable=False, default='standard')
    shipping_charge = db.Column(db.Float, default=0.0, nullable=False)
    estimated_delivery = db.Column(db.String(80), nullable=True)

    subtotal = db.Column(db.Float, default=0.0, nullable=False)
    product_discount = db.Column(db.Float, default=0.0, nullable=False)
    coupon_code = db.Column(db.String(40), nullable=True)
    coupon_discount = db.Column(db.Float, default=0.0, nullable=False)
    coins_redeemed = db.Column(db.Integer, default=0, nullable=False)
    coin_discount = db.Column(db.Float, default=0.0, nullable=False)
    gst_total = db.Column(db.Float, default=0.0, nullable=False)
    platform_fee = db.Column(db.Float, default=0.0, nullable=False)
    grand_total = db.Column(db.Float, default=0.0, nullable=False)

    status = db.Column(db.String(30), default='pending', nullable=False)
    payment_method = db.Column(db.String(30), nullable=False)
    payment_status = db.Column(db.String(30), default='pending', nullable=False)

    checkout_step = db.Column(db.String(30), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')
    payments = db.relationship('Payment', backref='order', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'orderNumber': self.order_number,
            'status': self.status,
            'grandTotal': float(self.grand_total or 0),
            'paymentMethod': self.payment_method,
            'paymentStatus': self.payment_status,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
        }


class OrderItem(db.Model):
    __tablename__ = 'order_items'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id', ondelete='SET NULL'), nullable=True)
    product_name = db.Column(db.String(200), nullable=False)
    product_sku = db.Column(db.String(80), nullable=True)
    variant = db.Column(db.String(120), nullable=True)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Float, nullable=False, default=0.0)
    line_total = db.Column(db.Float, nullable=False, default=0.0)
    image_url = db.Column(db.String(255), nullable=True)


class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False, index=True)
    method = db.Column(db.String(30), nullable=False)
    status = db.Column(db.String(30), default='pending', nullable=False)
    amount = db.Column(db.Float, nullable=False, default=0.0)
    transaction_id = db.Column(db.String(120), nullable=True)
    metadata_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class CheckoutInventoryLock(db.Model):
    __tablename__ = 'checkout_inventory_locks'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id', ondelete='CASCADE'), nullable=False, index=True)
    quantity = db.Column(db.Integer, nullable=False)
    lock_token = db.Column(db.String(64), nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class CheckoutAbandonment(db.Model):
    __tablename__ = 'checkout_abandonments'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True, index=True)
    guest_token = db.Column(db.String(64), nullable=True, index=True)
    cart_snapshot = db.Column(db.Text, nullable=True)
    last_step = db.Column(db.String(30), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
