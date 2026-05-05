from flask import Blueprint, render_template, url_for, jsonify, abort
from flask_login import login_required, current_user
from ..models import Product

customer_bp = Blueprint('customer', __name__)


@customer_bp.route('/')
@login_required
def shop_home():
    """Customer dashboard with products, cart, and orders"""
    return render_template('customer/dashboard.html', user=current_user)


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
