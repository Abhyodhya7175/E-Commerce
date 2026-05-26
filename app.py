from flask import redirect, url_for, jsonify, render_template
from flask_login import current_user
from flask_app.models import Product, OfferBanner
from flask_app.extensions import db
from datetime import datetime

from flask_app import create_app


app = create_app()

@app.route('/')
def home():
    '''if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        # Logged-in customers should still be able to view the marketing homepage.
        # (Shop pages remain available via their own routes.)'''

    # Fetch data for various sections (always fresh from DB)
    # Latest "Just Landed" products - newest 10 products ordered by created_at
    just_landed = [p.to_dict() for p in Product.query.filter_by(active=True).order_by(Product.created_at.desc()).limit(10).all()]

    # New arrivals - newest 4 products
    new_arrivals = [p.to_dict() for p in Product.query.filter_by(active=True).order_by(Product.created_at.desc()).limit(4).all()]

    trending_query = Product.query.filter_by(active=True, trending_product=True).order_by(Product.updated_at.desc())
    trending_products = [p.to_dict() for p in trending_query.limit(4).all()]
    if not trending_products:
        trending_products = [p.to_dict() for p in Product.query.filter_by(active=True).order_by(Product.updated_at.desc()).limit(4).all()]

    personalized_products = [p.to_dict() for p in Product.query.filter(Product.active == True, Product.category.ilike('electronics')).limit(4).all()]
    wishlisted_products = [p.to_dict() for p in Product.query.filter_by(active=True).offset(2).limit(4).all()]
    carousel_products = [p.to_dict() for p in Product.query.filter_by(active=True).order_by(Product.created_at.desc()).limit(8).all()]
    flash_deals = Product.query.filter_by(active=True).offset(6).limit(4).all()
    today = datetime.utcnow().date()
    offer_banners = [
        banner for banner in OfferBanner.query.filter_by(is_active=True).order_by(
            OfferBanner.display_order.asc(),
            OfferBanner.id.asc(),
        ).all()
        if (not banner.start_date or banner.start_date.date() <= today)
        and (not banner.end_date or banner.end_date.date() >= today)
    ]

    # Add optional display-only badges without overriding admin-managed fields.
    for idx, d in enumerate(new_arrivals + trending_products + personalized_products + wishlisted_products + carousel_products):
        d["freeGift"] = idx % 4 == 0

    response = render_template('home.html',
                          just_landed=just_landed,
                          new_arrivals=new_arrivals,
                          trending_products=trending_products,
                          personalized_products=personalized_products,
                          wishlisted_products=wishlisted_products,
                          carousel_products=carousel_products,
                          flash_deals=flash_deals,
                          offer_banners=offer_banners)

    # Disable caching to ensure product changes show immediately
    response_obj = app.make_response(response)
    response_obj.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response_obj.headers['Pragma'] = 'no-cache'
    response_obj.headers['Expires'] = '0'
    return response_obj


@app.route('/debug/products')
def debug_products():
    products = Product.query.all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'category': p.category,
        'brand': p.brand,
        'sku': p.sku,
        'mrp': p.mrp,
        'discount_price': p.discount_price,
        'short_description': p.short_description,
        'long_description': p.long_description,
        'highlights': p.highlights,
        'specifications': p.specifications,
    } for p in products])


@app.route('/health')
def health():
    return jsonify(status='ok')



if __name__ == '__main__':
    print("Starting Flask app...")
    app.run(debug=True)
