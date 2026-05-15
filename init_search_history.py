#!/usr/bin/env python
"""Initialize search history table in the database"""
from app import app
from flask_app.extensions import db
from flask_app.models import SearchHistory

with app.app_context():
    print("Creating SearchHistory table...")
    
    # Create the table if it doesn't exist
    db.create_all()
    
    # Verify the table was created
    inspector = db.inspect(db.engine)
    tables = inspector.get_table_names()
    
    if 'search_history' in tables:
        print("✓ SearchHistory table created successfully!")
        columns = [col['name'] for col in inspector.get_columns('search_history')]
        print(f"  Columns: {', '.join(columns)}")
    else:
        print("✗ Failed to create SearchHistory table")
    
    print("\nAll tables in database:")
    for table in tables:
        print(f"  - {table}")
