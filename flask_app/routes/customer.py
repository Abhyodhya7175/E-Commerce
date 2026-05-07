from flask import Blueprint, render_template, url_for, jsonify, abort,request
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
        d["freeShipping"] = idx % 3 == 0
        d["freeGift"] = idx % 4 == 0
    return render_template(
        'product/grid_page.html',
        title='Shop Products',
        eyebrow='Customer',
        products=enriched,
    )


@customer_bp.route('/api/products')
@login_required
def api_products():
    products = Product.query.order_by(Product.id.asc()).all()
    return jsonify(products=[product.to_dict() for product in products])


@customer_bp.route('/product/<int:id>')
@login_required
def product_detail(id):
    product = Product.query.get(id)
    if not product:
        abort(404)
    return render_template('shop/product.html', product=product)


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



