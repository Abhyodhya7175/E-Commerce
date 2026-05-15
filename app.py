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
    
    # Fetch data for various sections
    # Latest "Just Landed" products - newest 10 products ordered by created_at
    just_landed = [p.to_dict() for p in Product.query.filter_by(active=True).order_by(Product.created_at.desc()).limit(10).all()]
    
    # New arrivals - newest 4 products
    new_arrivals = [p.to_dict() for p in Product.query.filter_by(active=True).order_by(Product.created_at.desc()).limit(4).all()]
    
    trending_products = [p.to_dict() for p in Product.query.filter_by(active=True).limit(4).all()]
    personalized_products = [p.to_dict() for p in Product.query.filter_by(active=True, category='electronics').limit(4).all()]
    wishlisted_products = [p.to_dict() for p in Product.query.filter_by(active=True).offset(2).limit(4).all()]
    carousel_products = [p.to_dict() for p in Product.query.filter_by(active=True).order_by(Product.created_at.desc()).limit(8).all()]
    flash_deals = Product.query.filter_by(active=True).offset(6).limit(4).all()
    now = datetime.utcnow()
    offer_banners = OfferBanner.query.filter(
        OfferBanner.is_active.is_(True),
        db.or_(OfferBanner.start_date.is_(None), OfferBanner.start_date <= now),
        db.or_(OfferBanner.end_date.is_(None), OfferBanner.end_date >= now),
    ).order_by(OfferBanner.display_order.asc(), OfferBanner.id.asc()).all()

    # Add optional premium badges for UI richness
    for idx, d in enumerate(new_arrivals + trending_products + personalized_products + wishlisted_products + carousel_products):
        d["freeShipping"] = idx % 3 == 0
        d["freeGift"] = idx % 4 == 0

    return render_template('home.html', 
                          just_landed=just_landed,
                          new_arrivals=new_arrivals,
                          trending_products=trending_products,
                          personalized_products=personalized_products,
                          wishlisted_products=wishlisted_products,
                          carousel_products=carousel_products,
                          flash_deals=flash_deals,
                          offer_banners=offer_banners)


@app.route('/health')
def health():
    return jsonify(status='ok')



if __name__ == '__main__':
    print("Starting Flask app...")
    app.run(debug=True)
