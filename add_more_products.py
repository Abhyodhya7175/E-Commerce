#!/usr/bin/env python
"""Add additional products to the database"""
from app import app
from flask_app.extensions import db
from flask_app.models import Product

# New products to add (IDs 13-24)
new_products = [
    {
        'name': 'Ultra HD 4K Webcam',
        'category': 'Electronics',
        'mrp': 3999.0,
        'discount_price': 2999.0,
        'description': '1080p resolution, built-in mic, auto focus.',
        'icon': '📹',
    },
    {
        'name': 'Cotton Jersey T-Shirt',
        'category': 'Fashion',
        'mrp': 899.0,
        'discount_price': 599.0,
        'description': 'Soft, breathable, trendy designs.',
        'icon': '👕',
    },
    {
        'name': 'Professional Camera Tripod',
        'category': 'Electronics',
        'mrp': 1999.0,
        'discount_price': 1499.0,
        'description': 'Aluminum alloy, compact, quick-release head.',
        'icon': '📷',
    },
    {
        'name': 'Organic Green Tea Set',
        'category': 'Home',
        'mrp': 799.0,
        'discount_price': 549.0,
        'description': '100% natural, premium loose leaf tea.',
        'icon': '🍵',
    },
    {
        'name': 'Denim Jacket Classic',
        'category': 'Fashion',
        'mrp': 2499.0,
        'discount_price': 1799.0,
        'description': 'Premium denim, timeless style.',
        'icon': '🧥',
    },
    {
        'name': 'Resistance Bands Set',
        'category': 'Sports',
        'mrp': 1299.0,
        'discount_price': 899.0,
        'description': '5-band set, portable fitness equipment.',
        'icon': '💪',
    },
    {
        'name': 'Python Programming Guide',
        'category': 'Books',
        'mrp': 1299.0,
        'discount_price': 899.0,
        'description': 'Complete guide for beginners to advanced.',
        'icon': '🐍',
    },
    {
        'name': 'Wireless Mouse Pro',
        'category': 'Electronics',
        'mrp': 1599.0,
        'discount_price': 999.0,
        'description': 'Ergonomic design, 2.4GHz, 12-month battery.',
        'icon': '🖱️',
    },
    {
        'name': 'Wall Clock Modern',
        'category': 'Home',
        'mrp': 1499.0,
        'discount_price': 999.0,
        'description': 'Minimalist design, silent mechanism.',
        'icon': '⏰',
    },
    {
        'name': 'Running Shorts Mesh',
        'category': 'Sports',
        'mrp': 899.0,
        'discount_price': 599.0,
        'description': 'Breathable mesh, quick-dry technology.',
        'icon': '🩳',
    },
    {
        'name': 'Web Development Bootcamp',
        'category': 'Books',
        'mrp': 1599.0,
        'discount_price': 1099.0,
        'description': 'HTML, CSS, JavaScript, React mastery.',
        'icon': '💻',
    },
    {
        'name': 'USB-C Charging Hub',
        'category': 'Electronics',
        'mrp': 2299.0,
        'discount_price': 1699.0,
        'description': '7-in-1 hub, fast charging, compact.',
        'icon': '🔌',
    },
]

with app.app_context():
    added_count = 0
    skipped_count = 0
    
    for product_data in new_products:
        # Check if product already exists
        existing = Product.query.filter_by(name=product_data['name']).first()
        
        if existing:
            print(f"⊘ Skipped: {product_data['name']} (already exists)")
            skipped_count += 1
            continue
        
        # Create new product
        product = Product(
            name=product_data['name'],
            category=product_data['category'],
            mrp=product_data['mrp'],
            discount_price=product_data['discount_price'],
            description=product_data['description'],
            icon=product_data['icon'],
            active=True
        )
        
        db.session.add(product)
        print(f"✓ Added: {product_data['name']} (₹{product_data['mrp']} → ₹{product_data['discount_price']})")
        added_count += 1
    
    try:
        db.session.commit()
        print(f"\n✓ Successfully added {added_count} products!")
        if skipped_count > 0:
            print(f"⊘ Skipped {skipped_count} duplicate products")
        
        # Display total products count
        total = Product.query.count()
        print(f"\nTotal products in store: {total}")
        
    except Exception as e:
        db.session.rollback()
        print(f"\n✗ Error adding products: {e}")
