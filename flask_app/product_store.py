from __future__ import annotations

import json
from pathlib import Path


DATA_FILE = Path(__file__).resolve().parent / 'products.json'

DEFAULT_PRODUCTS = [
    {'id': 1, 'name': 'Wireless Noise-Cancelling Headphones', 'category': 'Electronics', 'mrp': 9999, 'discountPrice': 7999, 'desc': 'Premium audio with 30hr battery life.', 'icon': '🎧', 'active': True},
    {'id': 2, 'name': 'Mechanical Keyboard RGB', 'category': 'Electronics', 'mrp': 5499, 'discountPrice': 4299, 'desc': 'Tactile switches, full RGB backlight.', 'icon': '⌨️', 'active': True},
    {'id': 3, 'name': 'Slim Fit Cotton Shirt', 'category': 'Fashion', 'mrp': 1699, 'discountPrice': 1199, 'desc': '100% cotton, perfect for any occasion.', 'icon': '👔', 'active': True},
    {'id': 4, 'name': 'Running Shoes Pro', 'category': 'Sports', 'mrp': 4499, 'discountPrice': 3499, 'desc': 'Lightweight sole, breathable mesh upper.', 'icon': '👟', 'active': True},
    {'id': 5, 'name': 'Ceramic Coffee Mug Set', 'category': 'Home', 'mrp': 1199, 'discountPrice': 899, 'desc': 'Set of 4 hand-crafted ceramic mugs.', 'icon': '☕', 'active': True},
    {'id': 6, 'name': 'Yoga Mat Premium', 'category': 'Sports', 'mrp': 1999, 'discountPrice': 1599, 'desc': 'Non-slip, 6mm thick, eco-friendly.', 'icon': '🧘', 'active': False},
    {'id': 7, 'name': 'The Art of Clean Code', 'category': 'Books', 'mrp': 799, 'discountPrice': 549, 'desc': 'A bestselling guide for software craftsmanship.', 'icon': '📚', 'active': True},
    {'id': 8, 'name': 'Smart LED Desk Lamp', 'category': 'Electronics', 'mrp': 2799, 'discountPrice': 2199, 'desc': 'Touch controls, adjustable color temp.', 'icon': '💡', 'active': True},
    {'id': 9, 'name': 'Linen Throw Blanket', 'category': 'Home', 'mrp': 2399, 'discountPrice': 1899, 'desc': 'Soft woven linen, 140×180cm.', 'icon': '🛋️', 'active': True},
    {'id': 10, 'name': 'Sunglasses UV400', 'category': 'Fashion', 'mrp': 1099, 'discountPrice': 799, 'desc': 'Polarized lenses, lightweight frame.', 'icon': '🕶️', 'active': True},
    {'id': 11, 'name': 'Stainless Water Bottle', 'category': 'Sports', 'mrp': 999, 'discountPrice': 699, 'desc': '1L, keeps cold 24h, leak-proof cap.', 'icon': '🍶', 'active': True},
    {'id': 12, 'name': 'Design Thinking Handbook', 'category': 'Books', 'mrp': 999, 'discountPrice': 699, 'desc': 'Innovation methods used by top firms.', 'icon': '📖', 'active': True},
]


def _normalize_products(products):
    normalized = []
    for index, product in enumerate(products, start=1):
        normalized.append({
            'id': int(product.get('id', index)),
            'name': product.get('name', ''),
            'category': product.get('category', ''),
            'mrp': float(product.get('mrp', 0)),
            'discountPrice': float(product.get('discountPrice', 0)),
            'desc': product.get('desc', ''),
            'icon': product.get('icon', '📦'),
            'active': bool(product.get('active', True)),
        })
    return normalized


def _ensure_store():
    if not DATA_FILE.exists():
        with DATA_FILE.open('w', encoding='utf-8') as handle:
            json.dump(_normalize_products(DEFAULT_PRODUCTS), handle, ensure_ascii=False, indent=2)


def load_products():
    _ensure_store()
    with DATA_FILE.open('r', encoding='utf-8') as handle:
        return _normalize_products(json.load(handle))


def save_products(products):
    _ensure_store()
    with DATA_FILE.open('w', encoding='utf-8') as handle:
        json.dump(_normalize_products(products), handle, ensure_ascii=False, indent=2)


def next_product_id(products):
    return max((int(product['id']) for product in products), default=0) + 1


def upsert_product(product_data):
    products = load_products()
    product_id = int(product_data.get('id') or 0)
    if product_id:
        existing = next((product for product in products if product['id'] == product_id), None)
        if existing:
            existing.update({
                'name': product_data['name'],
                'category': product_data['category'],
                'mrp': float(product_data['mrp']),
                'discountPrice': float(product_data['discountPrice']),
                'desc': product_data.get('desc', ''),
                'icon': product_data.get('icon', existing.get('icon', '📦')),
                'active': bool(product_data.get('active', existing.get('active', True))),
            })
        else:
            product_data['id'] = product_id
            products.append(_normalize_products([product_data])[0])
    else:
        product_data['id'] = next_product_id(products)
        products.append(_normalize_products([product_data])[0])

    save_products(products)
    return products


def toggle_product(product_id):
    products = load_products()
    product = next((item for item in products if item['id'] == product_id), None)
    if product is None:
        return None

    product['active'] = not product['active']
    save_products(products)
    return product


def delete_product(product_id):
    products = load_products()
    new_products = [product for product in products if product['id'] != product_id]
    if len(new_products) == len(products):
        return False
    save_products(new_products)
    return True