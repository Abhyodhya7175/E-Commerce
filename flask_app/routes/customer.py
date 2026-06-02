from flask import Blueprint, render_template, url_for, jsonify, abort, request, make_response
import json
from flask_login import current_user, login_required
from ..models import Product,Review
from ..extensions import db
from ..shop_state import get_cart_payload, get_wishlist_payload

customer_bp = Blueprint('customer', __name__)


@customer_bp.route('/')
def shop_home():
    """Customer dashboard with products, cart, and orders"""
    user = current_user if current_user.is_authenticated else None
    # Provide an initial products payload to the template so the page
    # can render products server-side if the client fetch fails.
    products = Product.query.filter_by(active=True).order_by(Product.created_at.desc()).limit(24).all()
    products_payload = [p.to_dict() for p in products]
    return render_template('customer/dashboard.html', user=user, initial_products=products_payload)

@customer_bp.route('/products')
def products_page():
    # Support optional filtering via query param `filter`
    # - filter=new_arrivals : show products with new_arrival=True
    f = request.args.get('filter', '').strip().lower()
    query = Product.query.filter_by(active=True)
    if f in ('new_arrivals', 'new-arrivals', 'new'):
        query = query.filter_by(new_arrival=True).order_by(Product.created_at.desc())
    else:
        query = query.order_by(Product.id.desc())
    products = query.limit(24).all()
    enriched = [p.to_dict() for p in products]
    for idx, d in enumerate(enriched):
        d["freeGift"] = idx % 4 == 0
    response = make_response(render_template(
        'product/grid_page.html',
        title='Shop Products',
        eyebrow='Customer',
        products=enriched,
    ))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    return response


@customer_bp.route('/api/products')
def api_products():
    products = Product.query.filter_by(active=True).order_by(Product.created_at.desc()).all()
    payload = [product.to_dict() for product in products]
    response = make_response(jsonify(products=payload))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@customer_bp.route('/product/<int:id>')
def product_detail(id):
    product = Product.query.get(id)
    if not product:
        abort(404)
    product_data = product.to_dict()
    images = product_data.get("imageUrls") or ([product_data.get("imageUrl")] if product_data.get("imageUrl") else [])
    images = [url for url in images if url]
    reviews = Review.query.filter_by(product_id=product.id).order_by(Review.created_at.desc()).all()
    response = make_response(render_template('product/detail.html', product=product_data, images=images, reviews=reviews))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@customer_bp.route('/cart')
def cart():
    payload = get_cart_payload()
    return render_template('shop/cart.html', cart_payload=payload)


@customer_bp.route('/wishlist')
def wishlist():
    payload = get_wishlist_payload()
    return render_template('shop/wishlist.html', wishlist_payload=payload)


@customer_bp.route('/api/reviews/add', methods=['POST'])
@login_required
def add_review():

    data = request.get_json()

    product_id = data.get('product_id')
    name = data.get('name')
    message = data.get('message')
    rating = data.get('rating')

    if not all([product_id, name, message, rating]):
        return jsonify(error="All fields required"), 400

    review = Review(
        product_id=product_id,
        name=name,
        message=message,
        rating=rating
    )

    db.session.add(review)
    db.session.commit()

    return jsonify(success=True)



