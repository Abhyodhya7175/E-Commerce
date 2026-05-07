from flask import Blueprint, render_template, abort
from ..models import Product, _slugify


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

    product = match.to_dict()
    images = product.get("imageUrls") or ([product.get("imageUrl")] if product.get("imageUrl") else [])
    images = [u for u in images if u]

    return render_template("product/detail.html", product=product, images=images)

