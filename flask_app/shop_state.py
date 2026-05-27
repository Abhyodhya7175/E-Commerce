from __future__ import annotations

import secrets
from typing import Iterable

from flask import request, session
from flask_login import current_user

from .extensions import db
from .models import CartItem, Product, WishlistItem


GUEST_CART_KEY = 'guest_cart'
GUEST_WISHLIST_KEY = 'guest_wishlist'
CSRF_SESSION_KEY = 'shop_csrf_token'


def get_csrf_token() -> str:
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[CSRF_SESSION_KEY] = token
    return token


def validate_csrf_token() -> bool:
    if request.method in {'GET', 'HEAD', 'OPTIONS', 'TRACE'}:
        return True

    submitted = request.headers.get('X-CSRFToken') or request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
    expected = session.get(CSRF_SESSION_KEY)
    return bool(submitted and expected and secrets.compare_digest(str(submitted), str(expected)))


def _normalize_quantity(value) -> int:
    try:
        quantity = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, quantity)


def _guest_cart() -> dict[int, int]:
    raw = session.get(GUEST_CART_KEY, {})
    if not isinstance(raw, dict):
        return {}

    cart: dict[int, int] = {}
    for key, value in raw.items():
        try:
            product_id = int(key)
        except (TypeError, ValueError):
            continue
        quantity = _normalize_quantity(value)
        if quantity:
            cart[product_id] = cart.get(product_id, 0) + quantity
    return cart


def _write_guest_cart(cart: dict[int, int]) -> None:
    session[GUEST_CART_KEY] = {str(product_id): int(quantity) for product_id, quantity in cart.items() if int(quantity) > 0}
    session.modified = True


def _guest_wishlist() -> list[int]:
    raw = session.get(GUEST_WISHLIST_KEY, [])
    if not isinstance(raw, list):
        return []

    wishlist: list[int] = []
    seen: set[int] = set()
    for value in raw:
        try:
            product_id = int(value)
        except (TypeError, ValueError):
            continue
        if product_id not in seen:
            wishlist.append(product_id)
            seen.add(product_id)
    return wishlist


def _write_guest_wishlist(wishlist: Iterable[int]) -> None:
    session[GUEST_WISHLIST_KEY] = [int(product_id) for product_id in wishlist]
    session.modified = True


def _active_products_by_ids(product_ids: Iterable[int]) -> dict[int, Product]:
    ids = [int(product_id) for product_id in product_ids if product_id]
    if not ids:
        return {}
    products = Product.query.filter(Product.id.in_(ids), Product.active.is_(True)).all()
    return {product.id: product for product in products}


def _serialize_cart_line(product: Product, quantity: int) -> dict:
    payload = product.to_dict()
    quantity = max(1, int(quantity))
    line_total = round(float(payload['finalPrice'] or 0) * quantity, 2)
    mrp_total = round(float(payload['mrp'] or 0) * quantity, 2)
    discount_total = round(max(float(payload['mrp'] or 0) - float(payload['discountPrice'] or 0), 0) * quantity, 2)
    gst_total = round(float(payload['gstAmount'] or 0) * quantity, 2)
    shipping_total = 0.0 if payload.get('freeShipping') else round(float(payload.get('shippingCharges') or 0), 2)

    payload.update({
        'quantity': quantity,
        'lineTotal': line_total,
        'mrpTotal': mrp_total,
        'discountTotal': discount_total,
        'gstTotal': gst_total,
        'shippingTotal': shipping_total,
    })
    return payload


def get_cart_rows(user=None) -> list[dict]:
    if user is None:
        user = current_user

    if user.is_authenticated:
        rows = (
            CartItem.query
            .filter_by(user_id=user.id)
            .join(Product, CartItem.product_id == Product.id)
            .filter(Product.active.is_(True))
            .order_by(CartItem.created_at.desc())
            .all()
        )
        return [_serialize_cart_line(row.product, row.quantity) for row in rows if row.product]

    cart = _guest_cart()
    products = _active_products_by_ids(cart.keys())
    return [_serialize_cart_line(products[product_id], cart[product_id]) for product_id in cart if product_id in products]


def get_cart_summary(rows: list[dict]) -> dict:
    subtotal = round(sum(float(row['mrpTotal']) for row in rows), 2)
    discount_total = round(sum(float(row['discountTotal']) for row in rows), 2)
    gst_total = round(sum(float(row['gstTotal']) for row in rows), 2)
    shipping_total = round(sum(float(row['shippingTotal']) for row in rows), 2)
    total = round(sum(float(row['lineTotal']) for row in rows) + shipping_total, 2)

    return {
        'subtotal': subtotal,
        'discountTotal': discount_total,
        'gstTotal': gst_total,
        'shippingTotal': shipping_total,
        'total': total,
        'count': sum(int(row['quantity']) for row in rows),
    }


def get_cart_payload(user=None) -> dict:
    rows = get_cart_rows(user=user)
    return {
        'items': rows,
        'summary': get_cart_summary(rows),
    }


def get_wishlist_product_ids(user=None) -> list[int]:
    if user is None:
        user = current_user

    if user.is_authenticated:
        rows = (
            WishlistItem.query
            .filter_by(user_id=user.id)
            .join(Product, WishlistItem.product_id == Product.id)
            .filter(Product.active.is_(True))
            .order_by(WishlistItem.created_at.desc())
            .all()
        )
        return [row.product_id for row in rows if row.product]

    wishlist = _guest_wishlist()
    products = _active_products_by_ids(wishlist)
    return [product_id for product_id in wishlist if product_id in products]


def get_wishlist_payload(user=None) -> dict:
    if user is None:
        user = current_user

    product_ids = get_wishlist_product_ids(user=user)
    products = _active_products_by_ids(product_ids)
    items = [products[product_id].to_dict() for product_id in product_ids if product_id in products]
    return {
        'items': items,
        'count': len(items),
    }


def get_commerce_state(user=None) -> dict:
    if user is None:
        user = current_user

    cart_payload = get_cart_payload(user=user)
    wishlist_ids = get_wishlist_product_ids(user=user)
    return {
        'cart_count': cart_payload['summary']['count'],
        'wishlist_count': len(wishlist_ids),
        'wishlist_ids': set(wishlist_ids),
        'cart_quantities': {item['id']: item['quantity'] for item in cart_payload['items']},
    }


def _ensure_product(product_id: int) -> Product | None:
    try:
        product_id = int(product_id)
    except (TypeError, ValueError):
        return None
    product = db.session.get(Product, product_id)
    if not product or not product.active:
        return None
    return product


def add_to_cart(product_id: int, quantity: int = 1, user=None) -> dict:
    if user is None:
        user = current_user

    product = _ensure_product(product_id)
    if not product:
        return {'ok': False, 'error': 'Product is unavailable.'}

    quantity = max(1, _normalize_quantity(quantity) or 1)
    if product.stock_quantity <= 0:
        return {'ok': False, 'error': 'Product is out of stock.'}

    if user.is_authenticated:
        row = CartItem.query.filter_by(user_id=user.id, product_id=product.id).first()
        next_quantity = quantity + (row.quantity if row else 0)
        if next_quantity > product.stock_quantity:
            return {'ok': False, 'error': 'Requested quantity exceeds available stock.'}
        if row:
            row.quantity = next_quantity
        else:
            db.session.add(CartItem(user_id=user.id, product_id=product.id, quantity=next_quantity))
    else:
        cart = _guest_cart()
        next_quantity = quantity + cart.get(product.id, 0)
        if next_quantity > product.stock_quantity:
            return {'ok': False, 'error': 'Requested quantity exceeds available stock.'}
        cart[product.id] = next_quantity
        _write_guest_cart(cart)

    db.session.commit()
    return {'ok': True}


def update_cart_quantity(product_id: int, quantity: int, user=None) -> dict:
    if user is None:
        user = current_user

    product = _ensure_product(product_id)
    if not product:
        return {'ok': False, 'error': 'Product is unavailable.'}

    quantity = _normalize_quantity(quantity)
    if quantity > product.stock_quantity:
        return {'ok': False, 'error': 'Requested quantity exceeds available stock.'}

    if user.is_authenticated:
        row = CartItem.query.filter_by(user_id=user.id, product_id=product.id).first()
        if quantity <= 0:
            if row:
                db.session.delete(row)
        elif row:
            row.quantity = quantity
        else:
            db.session.add(CartItem(user_id=user.id, product_id=product.id, quantity=quantity))
    else:
        cart = _guest_cart()
        if quantity <= 0:
            cart.pop(product.id, None)
        else:
            cart[product.id] = quantity
        _write_guest_cart(cart)

    db.session.commit()
    return {'ok': True}


def remove_from_cart(product_id: int, user=None) -> dict:
    return update_cart_quantity(product_id, 0, user=user)


def toggle_wishlist(product_id: int, user=None) -> dict:
    if user is None:
        user = current_user

    product = _ensure_product(product_id)
    if not product:
        return {'ok': False, 'error': 'Product is unavailable.'}

    if user.is_authenticated:
        row = WishlistItem.query.filter_by(user_id=user.id, product_id=product.id).first()
        if row:
            db.session.delete(row)
            active = False
        else:
            db.session.add(WishlistItem(user_id=user.id, product_id=product.id))
            active = True
        db.session.commit()
        return {'ok': True, 'active': active}

    wishlist = _guest_wishlist()
    if product.id in wishlist:
        wishlist = [pid for pid in wishlist if pid != product.id]
        active = False
    else:
        wishlist.append(product.id)
        active = True
    _write_guest_wishlist(wishlist)
    return {'ok': True, 'active': active}


def remove_from_wishlist(product_id: int, user=None) -> dict:
    if user is None:
        user = current_user

    product = _ensure_product(product_id)
    if not product:
        return {'ok': False, 'error': 'Product is unavailable.'}

    if user.is_authenticated:
        row = WishlistItem.query.filter_by(user_id=user.id, product_id=product.id).first()
        if row:
            db.session.delete(row)
            db.session.commit()
    else:
        wishlist = [pid for pid in _guest_wishlist() if pid != product.id]
        _write_guest_wishlist(wishlist)
    return {'ok': True, 'active': False}


def move_wishlist_to_cart(product_id: int, quantity: int = 1, user=None) -> dict:
    if user is None:
        user = current_user

    add_result = add_to_cart(product_id, quantity=quantity, user=user)
    if not add_result.get('ok'):
        return add_result

    remove_from_wishlist(product_id, user=user)
    return {'ok': True}


def merge_guest_state_into_user(user_id: int) -> None:
    guest_cart = _guest_cart()
    guest_wishlist = _guest_wishlist()

    if guest_cart:
        products = _active_products_by_ids(guest_cart.keys())
        for product_id, quantity in guest_cart.items():
            product = products.get(product_id)
            if not product:
                continue
            row = CartItem.query.filter_by(user_id=user_id, product_id=product.id).first()
            next_quantity = quantity + (row.quantity if row else 0)
            if next_quantity > product.stock_quantity:
                next_quantity = product.stock_quantity
            if next_quantity <= 0:
                continue
            if row:
                row.quantity = next_quantity
            else:
                db.session.add(CartItem(user_id=user_id, product_id=product.id, quantity=next_quantity))

    if guest_wishlist:
        products = _active_products_by_ids(guest_wishlist)
        for product_id in guest_wishlist:
            product = products.get(product_id)
            if not product:
                continue
            if not WishlistItem.query.filter_by(user_id=user_id, product_id=product.id).first():
                db.session.add(WishlistItem(user_id=user_id, product_id=product.id))

    db.session.commit()
    session.pop(GUEST_CART_KEY, None)
    session.pop(GUEST_WISHLIST_KEY, None)
