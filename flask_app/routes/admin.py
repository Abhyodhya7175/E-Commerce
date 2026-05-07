from flask import Blueprint, render_template, abort, request, jsonify, current_app, url_for
from flask_login import login_required, current_user
from ..extensions import db
from ..models import User, Product, ProductImage
from werkzeug.utils import secure_filename
from uuid import uuid4
import os

admin_bp = Blueprint('admin', __name__, template_folder='../templates')


def _is_allowed_image(filename):
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in current_app.config.get('ALLOWED_IMAGE_EXTENSIONS', set())


def _save_product_image(file_storage):
    if not file_storage or not file_storage.filename:
        return None, None
    if not _is_allowed_image(file_storage.filename):
        return None, 'Invalid image format. Allowed: png, jpg, jpeg, webp, gif.'

    upload_subdir = current_app.config.get('PRODUCT_UPLOAD_SUBDIR', 'uploads/products')
    upload_dir = os.path.join(current_app.static_folder, *upload_subdir.split('/'))
    os.makedirs(upload_dir, exist_ok=True)

    original_name = secure_filename(file_storage.filename)
    ext = original_name.rsplit('.', 1)[1].lower()
    filename = f"{uuid4().hex}.{ext}"
    full_path = os.path.join(upload_dir, filename)
    file_storage.save(full_path)

    static_rel = f"{upload_subdir}/{filename}".replace('\\', '/')
    return url_for('static', filename=static_rel), None

def admin_required(fn):
    from functools import wraps

    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            abort(403)
        return fn(*args, **kwargs)

    return wrapper


@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    return render_template('admin/dashboard.html')

@admin_bp.route('/products')
@login_required
@admin_required
def products_grid():
    products = Product.query.order_by(Product.id.desc()).limit(24).all()
    enriched = [p.to_dict() for p in products]
    for idx, d in enumerate(enriched):
        d["freeShipping"] = idx % 3 == 0
        d["freeGift"] = idx % 4 == 0
    return render_template(
        'product/grid_page.html',
        title='Products',
        eyebrow='Admin',
        products=enriched,
    )


@admin_bp.route('/api/products')
@login_required
@admin_required
def api_products():
    products = Product.query.order_by(Product.id.asc()).all()
    return jsonify(products=[product.to_dict() for product in products])


@admin_bp.route('/add-user', methods=['POST'])
@login_required
@admin_required
def add_user():
    data = request.get_json()
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    role = data.get('role', 'customer')

    # Validate input
    if not name or not email or not password:
        return jsonify(error='All fields required'), 400
    if role not in ['admin', 'customer']:
        return jsonify(error='Invalid role'), 400

    # Check if email exists
    if User.query.filter_by(email=email).first():
        return jsonify(error='Email already registered'), 400

    # Create user
    user = User(name=name, email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return jsonify(success=True, user={
        'id': user.id,
        'name': user.name,
        'email': user.email,
        'role': user.role,
        'joined': 'Just now'
    }), 201


@admin_bp.route('/api/products/save', methods=['POST'])
@login_required
@admin_required
def save_product():
    data = request.form if request.form else (request.get_json() or {})
    name = str(data.get('name', '')).strip()
    category = str(data.get('category', '')).strip()
    desc = str(data.get('desc', '')).strip()
    icon = str(data.get('icon', '📦')).strip() or '📦'

    try:
        mrp = float(data.get('mrp', 0))
        discount_price = float(data.get('discountPrice', 0))
        product_id = int(data.get('id') or 0)
    except (TypeError, ValueError):
        return jsonify(error='Invalid product data'), 400

    if not name or not category:
        return jsonify(error='Name and category are required'), 400
    if mrp <= 0 or discount_price <= 0:
        return jsonify(error='MRP and discounted price must be greater than 0'), 400
    if discount_price > mrp:
        return jsonify(error='Discounted price cannot be greater than MRP'), 400

    product = Product.query.get(product_id) if product_id else Product()
    if product_id and not product:
        return jsonify(error='Product not found'), 404

    is_active = str(data.get('active', 'true')).lower() in ['1', 'true', 'yes', 'on']

    # Support multiple file uploads under 'images' (preferred) or single 'image' for backward compatibility
    uploaded_files = []
    if request.files:
        # flask's getlist will return [] if no such key
        uploaded_files = request.files.getlist('images') or (request.files.getlist('image') if 'image' in request.files else [])

    saved_image_urls = []
    for f in uploaded_files:
        if not f:
            continue
        url, err = _save_product_image(f)
        if err:
            return jsonify(error=err), 400
        if url:
            saved_image_urls.append(url)

    product.name = name
    product.category = category
    product.mrp = mrp
    product.discount_price = discount_price
    product.description = desc
    product.icon = icon
    product.active = is_active
    
    # Check if this is a new product
    is_new = not product_id or not product.id

    if is_new:
        db.session.add(product)
        # Flush to get the product ID if it's new
        db.session.flush()

    # If multiple images were uploaded, create ProductImage records; otherwise keep legacy image_url
    if saved_image_urls:
        # If updating existing product, preserve ordering by finding max existing order_index
        max_idx = db.session.query(db.func.max(ProductImage.order_index)).filter_by(product_id=product.id).scalar()
        base_index = (max_idx or 0) + 1
        
        for idx, img_url in enumerate(saved_image_urls):
            pi = ProductImage(product_id=product.id, image_url=img_url, order_index=base_index + idx)
            db.session.add(pi)
        
        # Also update legacy field for compatibility if it was empty
        if not product.image_url:
            product.image_url = saved_image_urls[0]

    db.session.commit()

    return jsonify(success=True, product=product.to_dict())


@admin_bp.route('/api/products/toggle/<int:product_id>', methods=['POST'])
@login_required
@admin_required
def api_toggle_product(product_id):
    product = db.session.get(Product, product_id)
    if product is None:
        return jsonify(error='Product not found'), 404
    product.active = not product.active
    db.session.commit()
    return jsonify(success=True, product=product.to_dict())


@admin_bp.route('/api/products/delete/<int:product_id>', methods=['POST'])
@login_required
@admin_required
def api_delete_product(product_id):
    product = db.session.get(Product, product_id)
    if not product:
        return jsonify(error='Product not found'), 404

    # Delete associated images from disk
    all_images = []
    if product.image_url:
        all_images.append(product.image_url)
    for img in product.images:
        all_images.append(img.image_url)

    for url in set(all_images):
        if url and '/static/' in url:
            try:
                rel = url.split('/static/', 1)[1]
                image_path = os.path.join(current_app.static_folder, *rel.split('/'))
                if os.path.exists(image_path):
                    os.remove(image_path)
            except Exception as e:
                print(f"Error deleting image: {e}")

    db.session.delete(product)
    db.session.commit()
    return jsonify(success=True)


@admin_bp.route('/api/products/image/delete', methods=['POST'])
@login_required
@admin_required
def api_delete_product_image():
    data = request.get_json() or {}
    try:
        product_id = int(data.get('productId') or 0)
    except (TypeError, ValueError):
        return jsonify(error='Invalid product ID'), 400

    image_url = str(data.get('imageUrl') or '').strip()
    if not product_id or not image_url:
        return jsonify(error='Product and image are required'), 400

    product = Product.query.get(product_id)
    if not product:
        return jsonify(error='Product not found'), 404

    # Remove matching ProductImage rows (including accidental duplicates)
    rows = ProductImage.query.filter_by(product_id=product_id, image_url=image_url).all()
    for row in rows:
        db.session.delete(row)

    # Remove file from disk if this is a local static file
    if '/static/' in image_url:
        rel = image_url.split('/static/', 1)[1]
        image_path = os.path.join(current_app.static_folder, *rel.split('/'))
        if os.path.exists(image_path):
            try:
                os.remove(image_path)
            except OSError:
                pass

    db.session.flush()

    remaining = ProductImage.query.filter_by(product_id=product_id).order_by(ProductImage.order_index.asc()).all()
    product.image_url = remaining[0].image_url if remaining else None
    db.session.commit()

    return jsonify(success=True, product=product.to_dict())
