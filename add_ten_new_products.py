#!/usr/bin/env python
"""Seed script: add ten new products marked as new arrivals"""
import re
from datetime import datetime

from app import app
from flask_app.extensions import db
from flask_app.models import Product


def slugify(value: str) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "product"


new_products = [
    { 'name': 'Smart LED Desk Lamp', 'category': 'Home', 'mrp': 2499.0, 'discount_price': 1799.0, 'description': 'Adjustable brightness, USB charging port.', 'icon': '💡' },
    { 'name': 'Eco Bamboo Toothbrush Pack', 'category': 'Home', 'mrp': 599.0, 'discount_price': 399.0, 'description': 'Pack of 4 biodegradable bamboo toothbrushes.', 'icon': '🪥' },
    { 'name': 'Noise Cancelling Earbuds', 'category': 'Electronics', 'mrp': 4999.0, 'discount_price': 3499.0, 'description': 'Compact earbuds with active noise cancellation.', 'icon': '🎧' },
    { 'name': 'Travel Backpack 30L', 'category': 'Fashion', 'mrp': 3999.0, 'discount_price': 2699.0, 'description': 'Durable, water-resistant, laptop compartment.', 'icon': '🎒' },
    { 'name': 'Stainless Steel Water Bottle 1L', 'category': 'Sports', 'mrp': 1299.0, 'discount_price': 899.0, 'description': 'Insulated bottle keeps drinks cold for 24h.', 'icon': '🥤' },
    { 'name': 'Gaming Mousepad XL', 'category': 'Electronics', 'mrp': 1499.0, 'discount_price': 999.0, 'description': 'Extra-large mousepad with stitched edges.', 'icon': '🖱️' },
    { 'name': 'Minimalist Wallet Slim', 'category': 'Fashion', 'mrp': 1299.0, 'discount_price': 799.0, 'description': 'RFID-blocking slim wallet for essentials.', 'icon': '💼' },
    { 'name': 'Yoga Mat Non-Slip', 'category': 'Sports', 'mrp': 1999.0, 'discount_price': 1299.0, 'description': 'Eco-friendly TPE material, extra cushioning.', 'icon': '🧘' },
    { 'name': 'Bluetooth Speaker Mini', 'category': 'Electronics', 'mrp': 2199.0, 'discount_price': 1499.0, 'description': 'Portable speaker with 10h battery life.', 'icon': '🔊' },
    { 'name': 'LED Book Light Clip', 'category': 'Books', 'mrp': 499.0, 'discount_price': 349.0, 'description': 'Flexible neck, 3 brightness levels.', 'icon': '📚' },
]


with app.app_context():
    added = 0
    skipped = 0
    for pdata in new_products:
        name = pdata['name']
        slug = slugify(name)
        # avoid duplicates by name or slug
        existing = Product.query.filter((Product.name == name) | (Product.slug == slug)).first()
        if existing:
            print(f"⊘ Skipped existing: {name}")
            skipped += 1
            continue

        p = Product(
            name=name,
            category=pdata.get('category', 'General'),
            mrp=pdata.get('mrp', 0.0),
            discount_price=pdata.get('discount_price', 0.0),
            description=pdata.get('description', ''),
            icon=pdata.get('icon', '📦'),
            slug=slug,
            active=True,
            stock_quantity=50,
            new_arrival=True,
            created_at=datetime.utcnow(),
        )
        db.session.add(p)
        print(f"✓ Queued: {name}")
        added += 1

    try:
        db.session.commit()
        print(f"\n✓ Committed: {added} added, {skipped} skipped")
        total = Product.query.count()
        print(f"Total products now: {total}")
    except Exception as e:
        db.session.rollback()
        print(f"✗ Error: {e}")
