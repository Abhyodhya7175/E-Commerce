from flask import redirect, url_for, jsonify, render_template
from flask_login import current_user
from flask_app.models import Product

from flask_app import create_app


app = create_app()

@app.route('/')
def home():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        # Logged-in customers should still be able to view the marketing homepage.
        # (Shop pages remain available via their own routes.)
    
    # Fetch data for various sections
    new_arrivals = Product.query.filter_by(active=True).order_by(Product.id.desc()).limit(4).all()
    trending_products = Product.query.filter_by(active=True).limit(4).all()
    personalized_products = Product.query.filter_by(active=True, category='electronics').limit(4).all()
    wishlisted_products = Product.query.filter_by(active=True).offset(2).limit(4).all()
    flash_deals = Product.query.filter_by(active=True).offset(6).limit(4).all()

    return render_template('home.html', 
                          new_arrivals=new_arrivals,
                          trending_products=trending_products,
                          personalized_products=personalized_products,
                          wishlisted_products=wishlisted_products,
                          flash_deals=flash_deals)


@app.route('/health')
def health():
    return jsonify(status='ok')



if __name__ == '__main__':
    print("Starting Flask app...")
    app.run(debug=True)
