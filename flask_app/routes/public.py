from flask import Blueprint, render_template, abort, jsonify, request
from flask_login import current_user
from ..models import Product, _slugify, Review, SearchHistory
from ..extensions import db


public_bp = Blueprint("public", __name__)


@public_bp.route("/cards")
def cards_demo():
    products = Product.query.order_by(Product.id.desc()).limit(12).all()
    # Enrich with optional flags so you can see badges.
    enriched = []
    for idx, p in enumerate(products):
        d = p.to_dict()
        d["freeShipping"] = idx % 3 == 0
        d["freeGift"] = idx % 4 == 0
        enriched.append(d)
    return render_template("product/cards_demo.html", products=enriched)


@public_bp.route("/product/<slug>")
def product_public(slug: str):
    # No DB schema migration needed: compute slug from name.
    products = Product.query.all()
    match = next((p for p in products if _slugify(p.name) == slug), None)
    if not match:
        abort(404)

    # Get all reviews for this product, ordered by newest first
    reviews = Review.query.filter_by(product_id=match.id).order_by(Review.created_at.desc()).all()
    
    product = match.to_dict()
    images = product.get("imageUrls") or ([product.get("imageUrl")] if product.get("imageUrl") else [])
    images = [u for u in images if u]

    return render_template("product/detail.html", product=product, images=images, reviews=reviews)


@public_bp.route("/api/carousel/products")
def carousel_products():
    """
    API endpoint for carousel products
    Returns products with optimized data for carousel display
    Query params:
      - category: filter by category (optional)
      - limit: max products to return (default: 12)
      - sort: 'newest' or 'featured' (default: 'newest')
    """
    try:
        limit = min(int(request.args.get('limit', 12)), 100)  # Cap at 100
        category = request.args.get('category')
        sort = request.args.get('sort', 'newest')
        
        query = Product.query
        
        if category:
            query = query.filter_by(category=category)
        
        if sort == 'featured':
            # Sort by average rating (most reviewed first)
            query = query.order_by(Product.id.desc())
        else:
            # Default: newest first
            query = query.order_by(Product.id.desc())
        
        products = query.limit(limit).all()
        
        # Enrich with carousel-specific data
        enriched = []
        for idx, p in enumerate(products):
            d = p.to_dict()
            d["freeShipping"] = idx % 3 == 0
            enriched.append(d)
        
        return jsonify({
            'success': True,
            'products': enriched,
            'count': len(enriched)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@public_bp.route("/api/product-suggestions")
def product_suggestions():
    """
    API endpoint to get product names for searchbar autocomplete
    Returns first 8 product names for dropdown suggestions
    """
    try:
        products = Product.query.filter_by(active=True).order_by(Product.id.desc()).limit(8).all()
        names = [p.name for p in products]
        
        return jsonify({
            'success': True,
            'suggestions': names
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@public_bp.route("/api/search/save", methods=["POST"])
def save_search():
    """
    API endpoint to save user search query to history
    Expects JSON: { query: string, category: string (optional) }
    """
    try:
        data = request.get_json()
        query = (data.get('query') or '').strip()
        category = (data.get('category') or '').strip() or None
        
        if not query:
            return jsonify({
                'success': False,
                'error': 'Query cannot be empty'
            }), 400
        
        # Get user ID (if logged in) and IP address
        user_id = current_user.id if current_user.is_authenticated else None
        ip_address = request.remote_addr
        
        # Create search history record
        search = SearchHistory(
            user_id=user_id,
            query=query,
            category=category,
            ip_address=ip_address
        )
        
        db.session.add(search)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Search saved'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@public_bp.route("/api/search/history")
def get_search_history():
    """
    API endpoint to get user's recent search history
    Returns last 10 searches for authenticated users
    """
    try:
        if not current_user.is_authenticated:
            return jsonify({
                'success': False,
                'error': 'Authentication required'
            }), 401
        
        # Get last 10 searches for this user
        searches = SearchHistory.query.filter_by(
            user_id=current_user.id
        ).order_by(
            SearchHistory.created_at.desc()
        ).limit(10).all()
        
        history = [s.to_dict() for s in searches]
        
        return jsonify({
            'success': True,
            'history': history,
            'count': len(history)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

