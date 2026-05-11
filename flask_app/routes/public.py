from flask import Blueprint, render_template, abort, jsonify, request
from ..models import Product, _slugify, Review


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


