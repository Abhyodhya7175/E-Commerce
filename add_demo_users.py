#!/usr/bin/env python
"""Add demo users to the database for testing"""
from app import app
from flask_app.extensions import db
from flask_app.models import User

with app.app_context():
    # Check if demo users already exist
    customer = User.query.filter_by(email='customer@demo.com').first()
    admin = User.query.filter_by(email='admin@demo.com').first()
    
    if not customer:
        customer = User(name='Alex Johnson', email='customer@demo.com', role='customer')
        customer.set_password('customer123')
        db.session.add(customer)
        print("✓ Created customer user: customer@demo.com")
    else:
        print("✓ Customer user already exists")
    
    if not admin:
        admin = User(name='Sara Admin', email='admin@demo.com', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        print("✓ Created admin user: admin@demo.com")
    else:
        print("✓ Admin user already exists")
    
    db.session.commit()
    print("\n✓ Demo users ready!")
