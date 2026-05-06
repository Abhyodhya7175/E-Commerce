from flask import redirect, url_for, jsonify, render_template
from flask_login import current_user

from flask_app import create_app


app = create_app()

@app.route('/')
def home():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('customer.shop_home'))
    return render_template('home.html')


@app.route('/health')
def health():
    return jsonify(status='ok')



if __name__ == '__main__':
    print("Starting Flask app...")
    app.run(debug=True)
