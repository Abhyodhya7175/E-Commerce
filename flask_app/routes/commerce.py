from flask import Blueprint, jsonify, make_response, render_template, request
from flask_login import current_user

from ..models import Product

from ..shop_state import (
    add_to_cart,
    get_cart_payload,
    get_wishlist_payload,
    move_wishlist_to_cart,
    remove_from_cart,
    remove_from_wishlist,
    toggle_wishlist,
    update_cart_quantity,
    validate_csrf_token,
)


commerce_bp = Blueprint('commerce', __name__)


def _cart_recommendations(cart_items: list[dict], limit: int = 8) -> list[dict]:
    categories: list[str] = []
    excluded_ids = {item.get('id') for item in cart_items if item.get('id')}
    for item in cart_items:
        category = (item.get('category') or '').strip()
        if category and category not in categories:
            categories.append(category)

    if not categories:
        products = Product.query.filter(Product.active.is_(True))
        if excluded_ids:
            products = products.filter(~Product.id.in_(excluded_ids))
        return [product.to_dict() for product in products.order_by(Product.created_at.desc()).limit(limit).all()]

    recommended: list[dict] = []
    seen_ids: set[int] = set()
    for category in categories:
        query = Product.query.filter(Product.active.is_(True), Product.category == category)
        if excluded_ids:
            query = query.filter(~Product.id.in_(excluded_ids))
        for product in query.order_by(Product.created_at.desc()).limit(limit).all():
            if product.id in seen_ids:
                continue
            recommended.append(product.to_dict())
            seen_ids.add(product.id)
            if len(recommended) >= limit:
                return recommended

    if len(recommended) < limit:
        query = Product.query.filter(Product.active.is_(True))
        if excluded_ids:
            query = query.filter(~Product.id.in_(excluded_ids))
        if seen_ids:
            query = query.filter(~Product.id.in_(seen_ids))
        for product in query.order_by(Product.created_at.desc()).all():
            if product.id in seen_ids:
                continue
            recommended.append(product.to_dict())
            seen_ids.add(product.id)
            if len(recommended) >= limit:
                break

    return recommended[:limit]


def _json_error(message: str, status: int = 400):
    return jsonify(success=False, error=message), status


@commerce_bp.route('/cart')
def cart_page():
    payload = get_cart_payload()
    recommendations = _cart_recommendations(payload.get('items', []), limit=8)
    response = make_response(render_template('shop/cart.html', cart_payload=payload, recommended_products=recommendations))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@commerce_bp.route('/wishlist')
def wishlist_page():
    payload = get_wishlist_payload()
    response = make_response(render_template('shop/wishlist.html', wishlist_payload=payload))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@commerce_bp.route('/cart/add/<int:product_id>', methods=['POST'])
def api_cart_add(product_id: int):
    if not validate_csrf_token():
        return _json_error('Invalid CSRF token.', 403)

    data = request.get_json(silent=True) or {}
    result = add_to_cart(product_id, quantity=data.get('quantity', 1), user=current_user)
    if not result.get('ok'):
        return _json_error(result.get('error', 'Unable to add to cart.'))

    payload = get_cart_payload()
    return jsonify(success=True, message='Added to Cart', cart_count=payload['summary']['count'], summary=payload['summary'], cart=payload['items'])


@commerce_bp.route('/cart/update/<int:product_id>', methods=['POST'])
def api_cart_update(product_id: int):
    if not validate_csrf_token():
        return _json_error('Invalid CSRF token.', 403)

    data = request.get_json(silent=True) or {}
    result = update_cart_quantity(product_id, data.get('quantity', 1), user=current_user)
    if not result.get('ok'):
        return _json_error(result.get('error', 'Unable to update cart.'))

    payload = get_cart_payload()
    return jsonify(success=True, message='Cart updated', cart_count=payload['summary']['count'], summary=payload['summary'], cart=payload['items'])


@commerce_bp.route('/cart/remove/<int:product_id>', methods=['POST'])
def api_cart_remove(product_id: int):
    if not validate_csrf_token():
        return _json_error('Invalid CSRF token.', 403)

    result = remove_from_cart(product_id, user=current_user)
    if not result.get('ok'):
        return _json_error(result.get('error', 'Unable to remove item from cart.'))

    payload = get_cart_payload()
    return jsonify(success=True, message='Removed from Cart', cart_count=payload['summary']['count'], summary=payload['summary'], cart=payload['items'])


@commerce_bp.route('/wishlist/add/<int:product_id>', methods=['POST'])
def api_wishlist_toggle(product_id: int):
    if not validate_csrf_token():
        return _json_error('Invalid CSRF token.', 403)

    result = toggle_wishlist(product_id, user=current_user)
    if not result.get('ok'):
        return _json_error(result.get('error', 'Unable to update wishlist.'))

    payload = get_wishlist_payload()
    message = 'Added to Wishlist' if result.get('active') else 'Removed from Wishlist'
    return jsonify(success=True, message=message, wishlist_count=payload['count'], active=result.get('active'), wishlist=payload['items'])


@commerce_bp.route('/wishlist/remove/<int:product_id>', methods=['POST'])
def api_wishlist_remove(product_id: int):
    if not validate_csrf_token():
        return _json_error('Invalid CSRF token.', 403)

    result = remove_from_wishlist(product_id, user=current_user)
    if not result.get('ok'):
        return _json_error(result.get('error', 'Unable to remove item from wishlist.'))

    payload = get_wishlist_payload()
    return jsonify(success=True, message='Removed from Wishlist', wishlist_count=payload['count'], active=False, wishlist=payload['items'])


@commerce_bp.route('/wishlist/move-to-cart/<int:product_id>', methods=['POST'])
def api_wishlist_move_to_cart(product_id: int):
    if not validate_csrf_token():
        return _json_error('Invalid CSRF token.', 403)

    data = request.get_json(silent=True) or {}
    result = move_wishlist_to_cart(product_id, quantity=data.get('quantity', 1), user=current_user)
    if not result.get('ok'):
        return _json_error(result.get('error', 'Unable to move item to cart.'))

    cart_payload = get_cart_payload()
    wishlist_payload = get_wishlist_payload()
    return jsonify(
        success=True,
        message='Moved to Cart',
        cart_count=cart_payload['summary']['count'],
        wishlist_count=wishlist_payload['count'],
        summary=cart_payload['summary'],
        cart=cart_payload['items'],
        wishlist=wishlist_payload['items'],
    )