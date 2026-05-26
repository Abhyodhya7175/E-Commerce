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
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='customer')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


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
