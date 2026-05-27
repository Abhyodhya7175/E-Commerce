from datetime import datetime, timedelta
import re

from flask import Blueprint, render_template, abort, jsonify, request, make_response, current_app
from flask_login import current_user
from ..models import Product, _slugify, Review, SearchHistory, PincodeServiceabilityCache
from ..extensions import db
from ..services.shiprocket import check_serviceability


public_bp = Blueprint("public", __name__)


PINCODE_PATTERN = re.compile(r"^[1-9][0-9]{5}$")


def _parse_bool(value, default=True) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _resolve_weight_kg(product: Product | None, weight_arg: float | None) -> float:
    if weight_arg:
        return max(float(weight_arg), 0.1)
    if product and product.product_weight:
        return max(float(product.product_weight), 0.1)
    return max(float(current_app.config.get("DEFAULT_PRODUCT_WEIGHT_KG", 0.5)), 0.1)


def _is_free_shipping(product: Product | None, order_value: float | None) -> bool:
    threshold = float(current_app.config.get("FREE_SHIPPING_MIN", 0) or 0)
    if product and product.free_shipping:
        return True
    if order_value is None:
        return False
    return threshold > 0 and order_value >= threshold


def _get_cached_serviceability(pincode: str, weight_kg: float, pickup_pincode: str | None) -> PincodeServiceabilityCache | None:
    ttl_seconds = int(current_app.config.get("SHIPROCKET_CACHE_TTL_SECONDS", 21600))
    if ttl_seconds <= 0:
        return None

    query = PincodeServiceabilityCache.query.filter_by(pincode=pincode)
    if pickup_pincode:
        query = query.filter_by(pickup_pincode=pickup_pincode)

    cached = query.order_by(PincodeServiceabilityCache.checked_at.desc()).first()
    if not cached:
        return None

    if cached.checked_at and cached.checked_at < datetime.utcnow() - timedelta(seconds=ttl_seconds):
        return None

    if cached.weight is not None and abs(float(cached.weight) - float(weight_kg)) > 0.05:
        return None
    return cached


@public_bp.route("/cards")
def cards_demo():
    products = Product.query.filter_by(active=True).order_by(Product.id.desc()).limit(12).all()
    # Enrich with optional flags so you can see badges.
    enriched = []
    for idx, p in enumerate(products):
        d = p.to_dict()
        d["freeGift"] = idx % 4 == 0
        enriched.append(d)
    return render_template("product/cards_demo.html", products=enriched)


@public_bp.route("/product/<slug>")
def product_public(slug: str):
    products = Product.query.filter_by(active=True).all()
    match = next((p for p in products if (p.slug or _slugify(p.name)) == slug or _slugify(p.name) == slug), None)
    if not match:
        abort(404)

    # Get all reviews for this product, ordered by newest first
    reviews = Review.query.filter_by(product_id=match.id).order_by(Review.created_at.desc()).all()

    product = match.to_dict()
    images = product.get("imageUrls") or ([product.get("imageUrl")] if product.get("imageUrl") else [])
    images = [u for u in images if u]

    response = make_response(render_template("product/detail.html", product=product, images=images, reviews=reviews))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


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

        query = Product.query.filter_by(active=True)

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
            enriched.append(d)

        response = make_response(jsonify({
            'success': True,
            'products': enriched,
            'count': len(enriched)
        }))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
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


@public_bp.route("/check-pincode/<pincode>")
def check_pincode(pincode: str):
    normalized = re.sub(r"\s+", "", pincode or "")
    if not PINCODE_PATTERN.match(normalized):
        return jsonify(error="Invalid Indian pincode."), 400

    product_id = request.args.get("product_id", type=int)
    weight_arg = request.args.get("weight", type=float)
    pickup_arg = request.args.get("pickup_pincode")
    order_value = request.args.get("order_value", type=float)
    cod_requested = _parse_bool(request.args.get("cod"), default=True)

    product = Product.query.get(product_id) if product_id else None
    if product and order_value is None:
        order_value = float(product.selling_price or product.discount_price or 0)

    weight_kg = _resolve_weight_kg(product, weight_arg)
    pickup_pincode = pickup_arg or current_app.config.get("SHIPROCKET_PICKUP_PINCODE")

    cached = _get_cached_serviceability(normalized, weight_kg, pickup_pincode)
    if cached:
        return jsonify({
            "available": bool(cached.serviceable),
            "courier": cached.courier_name,
            "eta": cached.eta,
            "cod": bool(cached.cod),
            "estimated_date": None,
            "free_shipping": _is_free_shipping(product, order_value),
            "pickup_pincode": pickup_pincode,
            "source": "cache",
        })

    try:
        result = check_serviceability(
            normalized,
            weight_kg,
            pickup_pincode=pickup_pincode,
            cod=cod_requested,
        )
    except RuntimeError:
        return jsonify(error="Shiprocket service is temporarily unavailable."), 502

    cache_entry = PincodeServiceabilityCache(
        pincode=normalized,
        pickup_pincode=pickup_pincode,
        weight=round(weight_kg, 2),
        serviceable=bool(result.get("available")),
        cod=bool(result.get("cod")),
        eta=result.get("eta_text"),
        courier_name=result.get("courier"),
        checked_at=datetime.utcnow(),
    )
    try:
        db.session.add(cache_entry)
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Failed to write pincode cache")

    return jsonify({
        "available": bool(result.get("available")),
        "courier": result.get("courier"),
        "eta": result.get("eta_text"),
        "cod": bool(result.get("cod")),
        "estimated_date": result.get("estimated_date"),
        "free_shipping": _is_free_shipping(product, order_value),
        "pickup_pincode": pickup_pincode,
        "source": "live",
    })

