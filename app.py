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
        return redirect(url_for('customer.shop_home'))
    
    # Fetch data for various sections
    trending_products = Product.query.filter_by(active=True).limit(4).all()
    personalized_products = Product.query.filter_by(active=True, category='electronics').limit(4).all()
    wishlisted_products = Product.query.filter_by(active=True).order_by(Product.id.desc()).limit(4).all()
    flash_deals = Product.query.filter_by(active=True).offset(4).limit(4).all()

    return render_template('home.html', 
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
