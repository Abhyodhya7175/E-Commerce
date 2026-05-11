from .extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import re
from datetime import datetime


def _slugify(value: str) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "product"


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


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(80), nullable=False)
    mrp = db.Column(db.Float, nullable=False)
    discount_price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(20), nullable=False, default='📦')
    image_url = db.Column(db.String(255), nullable=True)
    active = db.Column(db.Boolean, nullable=False, default=True)

    reviews = db.relationship(
        "Review",
        backref="product",
        lazy=True,
        cascade="all, delete-orphan")

    images = db.relationship(
    "ProductImage",
    backref="product",
    lazy=True,
    cascade="all, delete-orphan")

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


        image_urls = [img.image_url for img in self.images]

        if not image_urls and self.image_url:
            image_urls = [self.image_url]

        return {
            'id': self.id,
            'slug': _slugify(self.name),
            'name': self.name,
            'category': self.category,
            'mrp': mrp,
            'discountPrice': discount_price,
            'discountPercent': discount_percent,
            'desc': self.description or '',
            'icon': self.icon,
            'sku': f"UC-{(self.id or 0):05d}",
            'rating': self.average_rating,
            'reviewCount': self.review_count,
            'stockStatus': 'In Stock' if self.active else 'Out of Stock',
            'imageUrls': image_urls,
            'imageUrl': image_urls[0] if len(image_urls) else None,
            'active': self.active,
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
    


