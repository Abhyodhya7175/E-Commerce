from flask import Blueprint, render_template, url_for, jsonify, abort, request, make_response
from flask_login import login_required, current_user
from ..models import Product,Review
from ..extensions import db

customer_bp = Blueprint('customer', __name__)


@customer_bp.route('/')
@login_required
def shop_home():
    """Customer dashboard with products, cart, and orders"""
    return render_template('customer/dashboard.html', user=current_user)

@customer_bp.route('/products')
@login_required
def products_page():
    products = Product.query.filter_by(active=True).order_by(Product.id.desc()).limit(24).all()
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
    response.headers['Expires'] = '0'
    return response


@customer_bp.route('/api/products')
@login_required
def api_products():
    products = Product.query.filter_by(active=True).order_by(Product.created_at.desc()).all()
    payload = [product.to_dict() for product in products]
    response = make_response(jsonify(products=payload))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@customer_bp.route('/product/<int:id>')
@login_required
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
@login_required
def cart():
    cart_items = []
    total = 0
    return render_template('shop/cart.html', cart_items=cart_items, total=total)


@customer_bp.route('/checkout')
@login_required
def checkout():
    return render_template('shop/checkout.html')



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



