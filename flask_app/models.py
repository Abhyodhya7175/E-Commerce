from .extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


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
    
    # Relationship for multiple images
    images = db.relationship('ProductImage', backref='product', cascade='all, delete-orphan', lazy='joined', order_by='ProductImage.order_index')

    def to_dict(self):
        # Collect image URLs from related ProductImage rows, fallback to legacy image_url
        image_urls = []
        seen_urls = set()
        for img in (self.images or []):
            if not img.image_url or img.image_url in seen_urls:
                continue
            seen_urls.add(img.image_url)
            image_urls.append(img.image_url)
        if not image_urls and self.image_url:
            image_urls = [self.image_url]

        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'mrp': self.mrp,
            'discountPrice': self.discount_price,
            'desc': self.description or '',
            'icon': self.icon,
            'imageUrls': image_urls,
            'imageUrl': image_urls[0] if len(image_urls) else None,
            'active': self.active,
        }


class ProductImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id', ondelete='CASCADE'), nullable=False)
    image_url = db.Column(db.String(255), nullable=False)
    order_index = db.Column(db.Integer, nullable=False, default=0)